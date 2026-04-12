"""
HermesNexus Phase 3 - 回滚服务测试
测试回滚服务的各项功能
"""

import pytest
import asyncio
from datetime import datetime
from shared.models.rollback import (
    RollbackPlan,
    RollbackStep,
    RollbackType,
    RollbackStatus,
    FailureRecord,
    RecoveryPlan,
    RecoveryAction,
    FailureType,
    FailureSeverity,
)
from shared.services.rollback_service import (
    RollbackService,
    RollbackServiceConfig,
    get_rollback_service,
    create_rollback_service,
)


class TestRollbackService:
    """回滚服务测试类"""

    @pytest.fixture
    def rollback_service(self):
        """创建回滚服务实例（测试模式：100%成功率）"""
        # 在测试中使用100%成功率以避免随机失败
        config = RollbackServiceConfig(
            simulate_execution_success_rate=1.0,  # 100%执行成功率
            simulate_validation_success_rate=1.0,  # 100%验证成功率
        )
        return RollbackService(config=config)

    @pytest.fixture
    def sample_config_plan_data(self):
        """示例配置回滚计划数据"""
        return {
            "name": "配置回滚测试",
            "description": "测试配置文件回滚功能",
            "trigger_reason": "配置更新导致服务异常",
            "trigger_type": "manual",
            "triggered_by": "test-user",
            "rollback_type": RollbackType.CONFIG,
            "target_resources": ["/etc/app/config.json"],
            "original_task_id": "task-001",
            "priority": 5,
            "estimated_duration_seconds": 300,
        }

    @pytest.fixture
    def sample_failure_data(self):
        """示例故障数据"""
        return {
            "task_id": "task-001",
            "failure_type": FailureType.EXECUTION_FAILURE,
            "severity": FailureSeverity.HIGH,
            "error_message": "服务启动失败",
            "node_id": "node-001",
            "asset_id": "asset-001",
            "stack_trace": "Traceback (most recent call last):\n  File 'app.py', line 42",
        }

    def test_create_rollback_plan_config(
        self, rollback_service, sample_config_plan_data
    ):
        """测试创建配置回滚计划"""
        plan = rollback_service.create_rollback_plan(**sample_config_plan_data)

        assert plan is not None
        assert plan.plan_id.startswith("rollback-")
        assert plan.name == sample_config_plan_data["name"]
        assert plan.rollback_type == RollbackType.CONFIG
        assert plan.status == RollbackStatus.PLANNED
        assert len(plan.steps) > 0
        assert plan.estimated_risk_level in ["low", "medium", "high"]

    def test_create_rollback_plan_service(self, rollback_service):
        """测试创建服务回滚计划"""
        plan_data = {
            "name": "服务回滚测试",
            "description": "测试服务版本回滚功能",
            "trigger_reason": "新版本存在严重bug",
            "trigger_type": "auto",
            "triggered_by": "system",
            "rollback_type": RollbackType.SERVICE,
            "target_resources": ["core-api", "worker-service"],
            "priority": 3,
            "estimated_duration_seconds": 600,
        }

        plan = rollback_service.create_rollback_plan(**plan_data)

        assert plan is not None
        assert plan.rollback_type == RollbackType.SERVICE
        assert len(plan.steps) > 0

    def test_create_rollback_plan_device(self, rollback_service):
        """测试创建设备回滚计划"""
        plan_data = {
            "name": "设备回滚测试",
            "description": "测试设备固件回滚功能",
            "trigger_reason": "固件升级导致设备离线",
            "trigger_type": "manual",
            "triggered_by": "operator-001",
            "rollback_type": RollbackType.DEVICE,
            "target_resources": ["device-001", "device-002"],
            "priority": 2,
            "estimated_duration_seconds": 900,
        }

        plan = rollback_service.create_rollback_plan(**plan_data)

        assert plan is not None
        assert plan.rollback_type == RollbackType.DEVICE
        assert len(plan.steps) > 0

    def test_create_rollback_plan_task(self, rollback_service):
        """测试创建任务回滚计划"""
        plan_data = {
            "name": "任务回滚测试",
            "description": "测试任务执行回滚功能",
            "trigger_reason": "任务执行失败需要回滚",
            "trigger_type": "auto",
            "triggered_by": "system",
            "rollback_type": RollbackType.TASK,
            "target_resources": ["task-001"],
            "priority": 7,
            "estimated_duration_seconds": 180,
        }

        plan = rollback_service.create_rollback_plan(**plan_data)

        assert plan is not None
        assert plan.rollback_type == RollbackType.TASK
        assert len(plan.steps) > 0

    def test_rollback_steps_generation(self, rollback_service, sample_config_plan_data):
        """测试回滚步骤生成"""
        plan = rollback_service.create_rollback_plan(**sample_config_plan_data)

        # 验证步骤基本属性
        assert len(plan.steps) > 0

        for i, step in enumerate(plan.steps):
            assert step.step_id.startswith(f"{plan.plan_id}-step-")
            assert step.sequence == i + 1
            assert step.description is not None
            assert step.operation is not None
            assert step.status == RollbackStatus.PLANNED

    def test_rollback_step_validation_criteria(
        self, rollback_service, sample_config_plan_data
    ):
        """测试回滚步骤验证标准"""
        plan = rollback_service.create_rollback_plan(**sample_config_plan_data)

        # 验证步骤包含验证标准
        for step in plan.steps:
            if step.validation_criteria:
                assert isinstance(step.validation_criteria, list)
                assert len(step.validation_criteria) > 0

    @pytest.mark.asyncio
    async def test_execute_rollback_plan_success(
        self, rollback_service, sample_config_plan_data
    ):
        """测试成功执行回滚计划"""
        plan = rollback_service.create_rollback_plan(**sample_config_plan_data)

        # 执行回滚计划（自动确认）
        result_plan = await rollback_service.execute_rollback_plan(
            plan.plan_id, auto_confirm=True
        )

        assert result_plan.status == RollbackStatus.COMPLETED
        assert result_plan.started_at is not None
        assert result_plan.completed_at is not None
        assert result_plan.final_status == "success"
        assert result_plan.rollback_summary is not None

    @pytest.mark.asyncio
    async def test_execute_rollback_plan_requires_confirmation(
        self, rollback_service, sample_config_plan_data
    ):
        """测试回滚计划需要确认"""
        plan = rollback_service.create_rollback_plan(**sample_config_plan_data)

        # 执行回滚计划（不自动确认）
        result_plan = await rollback_service.execute_rollback_plan(
            plan.plan_id, auto_confirm=False
        )

        # 应该回到就绪状态
        assert result_plan.status == RollbackStatus.READY
        assert result_plan.started_at is None
        assert result_plan.completed_at is None

    def test_cancel_rollback_plan(self, rollback_service, sample_config_plan_data):
        """测试取消回滚计划"""
        plan = rollback_service.create_rollback_plan(**sample_config_plan_data)

        # 取消计划
        cancelled_plan = rollback_service.cancel_rollback_plan(plan.plan_id)

        assert cancelled_plan.status == RollbackStatus.CANCELLED
        assert cancelled_plan.final_status == "cancelled"
        assert cancelled_plan.completed_at is not None

    def test_cancel_rollback_plan_invalid_status(
        self, rollback_service, sample_config_plan_data
    ):
        """测试取消执行中的回滚计划（应失败）"""
        # 创建一个执行中的计划
        plan = rollback_service.create_rollback_plan(**sample_config_plan_data)
        plan.status = RollbackStatus.EXECUTING

        # 尝试取消应该失败
        with pytest.raises(ValueError, match="当前状态 EXECUTING 不允许取消"):
            rollback_service.cancel_rollback_plan(plan.plan_id)

    def test_get_rollback_plan(self, rollback_service, sample_config_plan_data):
        """测试获取回滚计划"""
        created_plan = rollback_service.create_rollback_plan(**sample_config_plan_data)

        # 获取计划
        retrieved_plan = rollback_service.get_rollback_plan(created_plan.plan_id)

        assert retrieved_plan is not None
        assert retrieved_plan.plan_id == created_plan.plan_id
        assert retrieved_plan.name == created_plan.name

    def test_get_rollback_plan_not_found(self, rollback_service):
        """测试获取不存在的回滚计划"""
        plan = rollback_service.get_rollback_plan("non-existent-plan")
        assert plan is None

    def test_list_rollback_plans_no_filter(
        self, rollback_service, sample_config_plan_data
    ):
        """测试列出所有回滚计划"""
        # 创建多个计划
        rollback_service.create_rollback_plan(**sample_config_plan_data)
        rollback_service.create_rollback_plan(
            **{**sample_config_plan_data, "name": "计划2"}
        )

        plans = rollback_service.list_rollback_plans()

        assert len(plans) >= 2

    def test_list_rollback_plans_with_status_filter(
        self, rollback_service, sample_config_plan_data
    ):
        """测试按状态过滤回滚计划"""
        # 创建计划
        plan = rollback_service.create_rollback_plan(**sample_config_plan_data)

        # 按状态过滤
        plans = rollback_service.list_rollback_plans(status=RollbackStatus.PLANNED)

        assert len(plans) >= 1
        assert all(p.status == RollbackStatus.PLANNED for p in plans)

    def test_list_rollback_plans_with_type_filter(
        self, rollback_service, sample_config_plan_data
    ):
        """测试按类型过滤回滚计划"""
        # 创建计划
        rollback_service.create_rollback_plan(**sample_config_plan_data)

        # 按类型过滤
        plans = rollback_service.list_rollback_plans(rollback_type=RollbackType.CONFIG)

        assert len(plans) >= 1
        assert all(
            any(step.rollback_type == RollbackType.CONFIG for step in p.steps)
            for p in plans
        )

    def test_create_failure_record(self, rollback_service, sample_failure_data):
        """测试创建故障记录"""
        failure = rollback_service.create_failure_record(**sample_failure_data)

        assert failure is not None
        assert failure.failure_id.startswith("failure-")
        assert failure.task_id == sample_failure_data["task_id"]
        assert failure.failure_type == sample_failure_data["failure_type"]
        assert failure.severity == sample_failure_data["severity"]
        assert failure.error_message == sample_failure_data["error_message"]
        assert failure.recovery_action in [action for action in RecoveryAction]

    def test_create_recovery_plan(self, rollback_service, sample_failure_data):
        """测试创建恢复计划"""
        # 先创建故障记录
        failure = rollback_service.create_failure_record(**sample_failure_data)

        # 创建恢复计划
        recovery_plan = rollback_service.create_recovery_plan(
            failure_id=failure.failure_id,
            recovery_action=RecoveryAction.RETRY,
            steps=["检查故障", "重试任务", "验证结果"],
            validation_criteria=["任务成功"],
            priority=5,
        )

        assert recovery_plan is not None
        assert recovery_plan.plan_id.startswith("recovery-")
        assert recovery_plan.failure_id == failure.failure_id
        assert recovery_plan.recovery_action == RecoveryAction.RETRY
        assert len(recovery_plan.steps) == 3
        assert recovery_plan.priority == 5

    def test_get_failure_record(self, rollback_service, sample_failure_data):
        """测试获取故障记录"""
        created_failure = rollback_service.create_failure_record(**sample_failure_data)

        # 获取故障记录
        retrieved_failure = rollback_service.get_failure_record(
            created_failure.failure_id
        )

        assert retrieved_failure is not None
        assert retrieved_failure.failure_id == created_failure.failure_id
        assert retrieved_failure.task_id == created_failure.task_id

    def test_get_failure_record_not_found(self, rollback_service):
        """测试获取不存在的故障记录"""
        failure = rollback_service.get_failure_record("non-existent-failure")
        assert failure is None

    def test_list_failure_records(self, rollback_service, sample_failure_data):
        """测试列出故障记录"""
        # 创建多个故障记录
        rollback_service.create_failure_record(**sample_failure_data)
        rollback_service.create_failure_record(
            **{**sample_failure_data, "task_id": "task-002"}
        )

        failures = rollback_service.list_failure_records()

        assert len(failures) >= 2

    def test_list_failure_records_with_filters(
        self, rollback_service, sample_failure_data
    ):
        """测试按条件过滤故障记录"""
        # 创建故障记录
        rollback_service.create_failure_record(**sample_failure_data)

        # 按任务ID过滤
        failures = rollback_service.list_failure_records(task_id="task-001")
        assert len(failures) >= 1
        assert all(f.task_id == "task-001" for f in failures)

        # 按故障类型过滤
        failures = rollback_service.list_failure_records(
            failure_type=FailureType.EXECUTION_FAILURE
        )
        assert len(failures) >= 1
        assert all(f.failure_type == FailureType.EXECUTION_FAILURE for f in failures)

    def test_get_rollback_statistics(self, rollback_service, sample_config_plan_data):
        """测试获取回滚统计信息"""
        # 创建一些回滚计划
        plan1 = rollback_service.create_rollback_plan(**sample_config_plan_data)
        plan1.status = RollbackStatus.COMPLETED

        plan2 = rollback_service.create_rollback_plan(
            **{**sample_config_plan_data, "name": "计划2"}
        )
        plan2.status = RollbackStatus.FAILED

        # 获取统计信息
        stats = rollback_service.get_statistics()

        assert stats.total_rollback_plans >= 2
        assert stats.successful_rollbacks >= 1
        assert stats.failed_rollbacks >= 1
        assert stats.success_rate >= 0.0
        assert isinstance(stats.by_type, dict)
        assert isinstance(stats.by_trigger, dict)

    def test_rollback_risk_assessment(self, rollback_service):
        """测试回滚风险评估"""
        # 测试不同类型的风险评估
        config_plan = rollback_service.create_rollback_plan(
            name="配置回滚",
            description="测试",
            trigger_reason="测试",
            trigger_type="manual",
            triggered_by="user",
            rollback_type=RollbackType.CONFIG,
            target_resources=["config"],
            priority=5,
            estimated_duration_seconds=300,
        )

        device_plan = rollback_service.create_rollback_plan(
            name="设备回滚",
            description="测试",
            trigger_reason="测试",
            trigger_type="manual",
            triggered_by="user",
            rollback_type=RollbackType.DEVICE,
            target_resources=["device"],
            priority=5,
            estimated_duration_seconds=900,
        )

        # 设备回滚的风险应该高于配置回滚
        risk_order = {"low": 1, "medium": 2, "high": 3}
        assert (
            risk_order[device_plan.estimated_risk_level]
            >= risk_order[config_plan.estimated_risk_level]
        )

    def test_global_rollback_service(self):
        """测试全局回滚服务"""
        service = get_rollback_service()
        assert service is not None
        assert isinstance(service, RollbackService)

    def test_custom_rollback_service_config(self):
        """测试自定义回滚服务配置"""
        config = RollbackServiceConfig(
            default_timeout_seconds=600, default_max_retries=5, parallel_execution=True
        )

        service = create_rollback_service(config)
        assert service is not None
        assert service.config.default_timeout_seconds == 600
        assert service.config.default_max_retries == 5
        assert service.config.parallel_execution is True


@pytest.mark.integration
class TestRollbackServiceIntegration:
    """回滚服务集成测试"""

    @pytest.fixture
    def rollback_service(self):
        """创建回滚服务实例（测试模式：100%成功率）"""
        # 在测试中使用100%成功率以避免随机失败
        config = RollbackServiceConfig(
            simulate_execution_success_rate=1.0,  # 100%执行成功率
            simulate_validation_success_rate=1.0,  # 100%验证成功率
        )
        return RollbackService(config=config)

    @pytest.mark.asyncio
    async def test_full_rollback_workflow(self, rollback_service):
        """测试完整回滚工作流"""
        # 1. 创建故障记录
        failure = rollback_service.create_failure_record(
            task_id="task-001",
            failure_type=FailureType.APPROVAL_REJECTED,
            severity=FailureSeverity.HIGH,
            error_message="审批被拒绝，需要回滚",
        )

        # 2. 创建回滚计划
        rollback_plan = rollback_service.create_rollback_plan(
            name="审批拒绝回滚",
            description="因审批拒绝触发的自动回滚",
            trigger_reason=failure.error_message,
            trigger_type="auto",
            triggered_by="system",
            rollback_type=RollbackType.TASK,
            target_resources=["task-001"],
            original_task_id=failure.task_id,
            priority=3,
        )

        # 3. 执行回滚计划
        executed_plan = await rollback_service.execute_rollback_plan(
            rollback_plan.plan_id, auto_confirm=True
        )

        # 4. 验证结果
        assert executed_plan.status == RollbackStatus.COMPLETED
        assert executed_plan.final_status == "success"

        # 5. 检查统计信息
        stats = rollback_service.get_statistics()
        assert stats.total_rollback_plans >= 1
        assert stats.successful_rollbacks >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
