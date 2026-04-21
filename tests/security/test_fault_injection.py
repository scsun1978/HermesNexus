"""
HermesNexus Phase 3 - 故障注入测试
测试故障恢复机制的有效性和鲁棒性
"""

import pytest
import asyncio
from datetime import datetime
import uuid
import random
import time

from shared.models.rollback import (
    RollbackType,
    RollbackStatus,
    FailureRecord,
    RecoveryAction,
    FailureType,
    FailureSeverity,
)
from shared.services.rollback_service import get_rollback_service
from shared.services.recovery_service import get_recovery_service


class FaultInjector:
    """故障注入器 - 用于模拟各种故障场景"""

    def __init__(self):
        self.injected_faults = []
        self.fault_history = []

    def inject_network_failure(
        self, node_id: str, severity: FailureSeverity = FailureSeverity.MEDIUM
    ):
        """注入网络故障"""
        fault = {
            "fault_id": f"fault-network-{uuid.uuid4().hex[:8]}",
            "fault_type": FailureType.NETWORK_FAILURE,
            "severity": severity,
            "target": node_id,
            "description": f"网络连接故障: {node_id}",
            "simulation": lambda: self._simulate_network_timeout(node_id),
        }
        self.injected_faults.append(fault)
        return fault

    def inject_execution_failure(
        self, task_id: str, severity: FailureSeverity = FailureSeverity.HIGH
    ):
        """注入执行失败"""
        fault = {
            "fault_id": f"fault-exec-{uuid.uuid4().hex[:8]}",
            "fault_type": FailureType.EXECUTION_FAILURE,
            "severity": severity,
            "target": task_id,
            "description": f"任务执行失败: {task_id}",
            "simulation": lambda: self._simulate_execution_error(task_id),
        }
        self.injected_faults.append(fault)
        return fault

    def inject_timeout_failure(
        self, operation: str, severity: FailureSeverity = FailureSeverity.MEDIUM
    ):
        """注入超时故障"""
        fault = {
            "fault_id": f"fault-timeout-{uuid.uuid4().hex[:8]}",
            "fault_type": FailureType.TIMEOUT_FAILURE,
            "severity": severity,
            "target": operation,
            "description": f"操作超时: {operation}",
            "simulation": lambda: self._simulate_timeout(operation),
        }
        self.injected_faults.append(fault)
        return fault

    def inject_approval_rejection(
        self, request_id: str, severity: FailureSeverity = FailureSeverity.HIGH
    ):
        """注入审批拒绝"""
        fault = {
            "fault_id": f"fault-approval-{uuid.uuid4().hex[:8]}",
            "fault_type": FailureType.APPROVAL_REJECTED,
            "severity": severity,
            "target": request_id,
            "description": f"审批被拒绝: {request_id}",
            "simulation": lambda: self._simulate_approval_rejection(request_id),
        }
        self.injected_faults.append(fault)
        return fault

    def inject_configuration_error(
        self, config_file: str, severity: FailureSeverity = FailureSeverity.HIGH
    ):
        """注入配置错误"""
        fault = {
            "fault_id": f"fault-config-{uuid.uuid4().hex[:8]}",
            "fault_type": FailureType.CONFIGURATION_ERROR,
            "severity": severity,
            "target": config_file,
            "description": f"配置错误: {config_file}",
            "simulation": lambda: self._simulate_config_error(config_file),
        }
        self.injected_faults.append(fault)
        return fault

    def inject_resource_exhaustion(
        self, resource_type: str, severity: FailureSeverity = FailureSeverity.CRITICAL
    ):
        """注入资源耗尽"""
        fault = {
            "fault_id": f"fault-resource-{uuid.uuid4().hex[:8]}",
            "fault_type": FailureType.RESOURCE_EXHAUSTION,
            "severity": severity,
            "target": resource_type,
            "description": f"资源耗尽: {resource_type}",
            "simulation": lambda: self._simulate_resource_exhaustion(resource_type),
        }
        self.injected_faults.append(fault)
        return fault

    def _simulate_network_timeout(self, node_id: str):
        """模拟网络超时"""
        time.sleep(0.1)  # 模拟网络延迟
        raise ConnectionError(f"Network timeout connecting to {node_id}")

    def _simulate_execution_error(self, task_id: str):
        """模拟执行错误"""
        raise RuntimeError(f"Execution failed for task {task_id}")

    def _simulate_timeout(self, operation: str):
        """模拟超时"""
        time.sleep(0.5)  # 模拟长时间等待
        raise TimeoutError(f"Operation {operation} timed out")

    def _simulate_approval_rejection(self, request_id: str):
        """模拟审批拒绝"""
        return {"status": "rejected", "reason": "Test rejection"}

    def _simulate_config_error(self, config_file: str):
        """模拟配置错误"""
        raise ValueError(f"Invalid configuration in {config_file}")

    def _simulate_resource_exhaustion(self, resource_type: str):
        """模拟资源耗尽"""
        raise MemoryError(f"Resource exhaustion: {resource_type}")

    def trigger_fault(self, fault_id: str):
        """触发指定的故障"""
        for fault in self.injected_faults:
            if fault["fault_id"] == fault_id:
                self.fault_history.append(
                    {
                        "fault_id": fault_id,
                        "triggered_at": datetime.utcnow(),
                        "fault_type": fault["fault_type"],
                    }
                )
                return fault["simulation"]()

        raise ValueError(f"Fault not found: {fault_id}")

    def clear_faults(self):
        """清除所有注入的故障"""
        self.injected_faults.clear()


class TestFaultInjection:
    """故障注入测试类"""

    @pytest.fixture
    def fault_injector(self):
        """创建故障注入器"""
        return FaultInjector()

    @pytest.fixture
    def recovery_service(self):
        """创建恢复服务"""
        return get_recovery_service()

    @pytest.fixture
    def rollback_service(self):
        """创建回滚服务"""
        return get_rollback_service()

    @pytest.mark.asyncio
    async def test_network_failure_recovery(self, fault_injector, recovery_service):
        """测试网络故障的恢复"""
        # 1. 注入网络故障
        fault = fault_injector.inject_network_failure("node-001", FailureSeverity.MEDIUM)

        # 2. 触发故障并创建故障记录
        try:
            fault_injector.trigger_fault(fault["fault_id"])
        except ConnectionError as e:
            # 3. 创建故障记录
            failure = await recovery_service.handle_failure(
                task_id="task-network-001",
                failure_type=FailureType.NETWORK_FAILURE,
                severity=FailureSeverity.MEDIUM,
                error_message=str(e),
                node_id="node-001",
                auto_process=False,
            )

            assert failure.failure_type == FailureType.NETWORK_FAILURE
            assert failure.recovery_action in [
                RecoveryAction.RETRY,
                RecoveryAction.ESCALATE,
            ]

            # 4. 验证故障被正确分类
            assert failure.severity == FailureSeverity.MEDIUM

    @pytest.mark.asyncio
    async def test_execution_failure_recovery(self, fault_injector, recovery_service):
        """测试执行失败的恢复"""
        # 1. 注入执行失败
        fault = fault_injector.inject_execution_failure("task-exec-001", FailureSeverity.HIGH)

        # 2. 触发故障
        try:
            fault_injector.trigger_fault(fault["fault_id"])
        except RuntimeError as e:
            # 3. 创建故障记录
            failure = await recovery_service.handle_failure(
                task_id="task-exec-001",
                failure_type=FailureType.EXECUTION_FAILURE,
                severity=FailureSeverity.HIGH,
                error_message=str(e),
                auto_process=False,
            )

            assert failure.failure_type == FailureType.EXECUTION_FAILURE
            # 高严重程度的执行失败应该触发回滚或升级
            assert failure.recovery_action in [
                RecoveryAction.ROLLBACK,
                RecoveryAction.ESCALATE,
            ]

    @pytest.mark.asyncio
    async def test_timeout_failure_recovery(self, fault_injector, recovery_service):
        """测试超时故障的恢复"""
        # 1. 注入超时故障
        fault = fault_injector.inject_timeout_failure("api_call", FailureSeverity.MEDIUM)

        # 2. 触发故障
        try:
            fault_injector.trigger_fault(fault["fault_id"])
        except TimeoutError as e:
            # 3. 创建故障记录
            failure = await recovery_service.handle_failure(
                task_id="task-timeout-001",
                failure_type=FailureType.TIMEOUT_FAILURE,
                severity=FailureSeverity.MEDIUM,
                error_message=str(e),
                auto_process=False,
            )

            assert failure.failure_type == FailureType.TIMEOUT_FAILURE
            assert failure.recovery_action == RecoveryAction.ROLLBACK

    @pytest.mark.asyncio
    async def test_approval_rejection_rollback(self, fault_injector, rollback_service):
        """测试审批拒绝触发回滚"""
        # 1. 注入审批拒绝
        fault = fault_injector.inject_approval_rejection("approval-001", FailureSeverity.MEDIUM)

        # 2. 触发故障
        result = fault_injector.trigger_fault(fault["fault_id"])

        if result.get("status") == "rejected":
            # 3. 创建故障记录
            failure = rollback_service.create_failure_record(
                task_id="task-approval-001",
                failure_type=FailureType.APPROVAL_REJECTED,
                severity=FailureSeverity.MEDIUM,
                error_message=f"审批被拒绝: {result.get('reason')}",
                context={"approval_id": "approval-001"},
            )

            assert failure.failure_type == FailureType.APPROVAL_REJECTED
            assert failure.recovery_action == RecoveryAction.ROLLBACK

            # 4. 创建回滚计划
            rollback_plan = rollback_service.create_rollback_plan(
                name="审批拒绝回滚",
                description=f"因审批拒绝触发的回滚: {result.get('reason')}",
                trigger_reason=failure.error_message,
                trigger_type="auto",
                triggered_by="system",
                rollback_type=RollbackType.TASK,
                target_resources=["task-approval-001"],
                original_task_id=failure.task_id,
            )

            assert rollback_plan.status == RollbackStatus.PLANNED
            assert len(rollback_plan.steps) > 0

    @pytest.mark.asyncio
    async def test_configuration_error_recovery(self, fault_injector, recovery_service):
        """测试配置错误的恢复"""
        # 1. 注入配置错误
        fault = fault_injector.inject_configuration_error(
            "/etc/app/config.json", FailureSeverity.HIGH
        )

        # 2. 触发故障
        try:
            fault_injector.trigger_fault(fault["fault_id"])
        except ValueError as e:
            # 3. 创建故障记录
            failure = await recovery_service.handle_failure(
                task_id="task-config-001",
                failure_type=FailureType.CONFIGURATION_ERROR,
                severity=FailureSeverity.MEDIUM,
                error_message=str(e),
                auto_process=False,
            )

            assert failure.failure_type == FailureType.CONFIGURATION_ERROR
            # 配置错误应该触发回滚
            assert failure.recovery_action == RecoveryAction.ROLLBACK

    @pytest.mark.asyncio
    async def test_resource_exhaustion_recovery(self, fault_injector, recovery_service):
        """测试资源耗尽的恢复"""
        # 1. 注入资源耗尽
        fault = fault_injector.inject_resource_exhaustion("memory", FailureSeverity.HIGH)

        # 2. 触发故障
        try:
            fault_injector.trigger_fault(fault["fault_id"])
        except MemoryError as e:
            # 3. 创建故障记录
            failure = await recovery_service.handle_failure(
                task_id="task-resource-001",
                failure_type=FailureType.RESOURCE_EXHAUSTION,
                severity=FailureSeverity.HIGH,
                error_message=str(e),
                auto_process=False,
            )

            assert failure.failure_type == FailureType.RESOURCE_EXHAUSTION
            # 资源耗尽应该回滚处理
            assert failure.recovery_action == RecoveryAction.ROLLBACK

    @pytest.mark.asyncio
    async def test_cascading_failures(self, fault_injector, recovery_service):
        """测试级联故障"""
        # 1. 注入多个相关故障
        network_fault = fault_injector.inject_network_failure("node-001", FailureSeverity.MEDIUM)
        timeout_fault = fault_injector.inject_timeout_failure("api_call", FailureSeverity.MEDIUM)
        exec_fault = fault_injector.inject_execution_failure(
            "task-cascade-001", FailureSeverity.HIGH
        )

        # 2. 模拟级联故障场景
        failures = []
        try:
            # 网络故障导致超时
            fault_injector.trigger_fault(network_fault["fault_id"])
        except ConnectionError:
            failures.append(("network", FailureType.NETWORK_FAILURE))

            try:
                # 网络故障导致API超时
                fault_injector.trigger_fault(timeout_fault["fault_id"])
            except TimeoutError:
                failures.append(("timeout", FailureType.TIMEOUT_FAILURE))

                try:
                    # 超时导致执行失败
                    fault_injector.trigger_fault(exec_fault["fault_id"])
                except RuntimeError:
                    failures.append(("execution", FailureType.EXECUTION_FAILURE))

        # 3. 验证级联故障被正确处理
        assert len(failures) == 3

        # 4. 创建最终的故障记录
        final_failure = await recovery_service.handle_failure(
            task_id="task-cascade-001",
            failure_type=FailureType.EXECUTION_FAILURE,
            severity=FailureSeverity.HIGH,
            error_message="级联故障：网络->超时->执行失败",
            context={
                "cascade_chain": [f[1].value for f in failures],
                "root_cause": FailureType.NETWORK_FAILURE.value,
            },
            auto_process=False,
        )

        assert final_failure.context["cascade_chain"] == [
            "network_failure",
            "timeout_failure",
            "execution_failure",
        ]

    @pytest.mark.asyncio
    async def test_recovery_action_effectiveness(
        self, fault_injector, recovery_service, rollback_service
    ):
        """测试恢复动作的有效性"""
        # 测试每种恢复动作

        # 1. RETRY - 针对网络故障
        network_fault = fault_injector.inject_network_failure("node-retry", FailureSeverity.LOW)
        try:
            fault_injector.trigger_fault(network_fault["fault_id"])
        except ConnectionError:
            failure = await recovery_service.handle_failure(
                task_id="task-retry-001",
                failure_type=FailureType.NETWORK_FAILURE,
                severity=FailureSeverity.LOW,
                error_message="网络故障，需要重试",
                auto_process=False,
            )
            assert failure.recovery_action == RecoveryAction.RETRY

        # 2. ROLLBACK - 针对审批拒绝
        approval_fault = fault_injector.inject_approval_rejection(
            "approval-rollback", FailureSeverity.MEDIUM
        )
        result = fault_injector.trigger_fault(approval_fault["fault_id"])
        if result.get("status") == "rejected":
            failure = rollback_service.create_failure_record(
                task_id="task-rollback-001",
                failure_type=FailureType.APPROVAL_REJECTED,
                severity=FailureSeverity.MEDIUM,
                error_message="审批拒绝，需要回滚",
            )
            assert failure.recovery_action == RecoveryAction.ROLLBACK

        # 3. ESCALATE - 针对资源耗尽
        resource_fault = fault_injector.inject_resource_exhaustion("cpu", FailureSeverity.MEDIUM)
        try:
            fault_injector.trigger_fault(resource_fault["fault_id"])
        except MemoryError:
            failure = await recovery_service.handle_failure(
                task_id="task-escalate-001",
                failure_type=FailureType.RESOURCE_EXHAUSTION,
                severity=FailureSeverity.MEDIUM,
                error_message="资源耗尽，需要升级处理",
                auto_process=False,
            )
            assert failure.recovery_action == RecoveryAction.ESCALATE


@pytest.mark.stress
class TestFaultInjectionStress:
    """故障注入压力测试"""

    @pytest.fixture
    def fault_injector(self):
        """创建故障注入器"""
        return FaultInjector()

    @pytest.mark.asyncio
    async def test_concurrent_failures(self, fault_injector):
        """测试并发故障处理"""
        # 1. 同时注入多个故障
        faults = []
        for i in range(10):
            fault = fault_injector.inject_network_failure(
                f"node-concurrent-{i}", FailureSeverity.MEDIUM
            )
            faults.append(fault)

        # 2. 并发触发故障
        recovery_service = get_recovery_service()
        tasks = []

        for fault in faults:

            async def trigger_and_handle(f):
                try:
                    fault_injector.trigger_fault(f["fault_id"])
                except ConnectionError:
                    failure = await recovery_service.handle_failure(
                        task_id=f"task-concurrent-{f['fault_id']}",
                        failure_type=FailureType.NETWORK_FAILURE,
                        severity=FailureSeverity.MEDIUM,
                        error_message="并发网络故障",
                        auto_process=False,
                    )
                    return failure

            tasks.append(trigger_and_handle(fault))

        # 3. 并发处理
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 4. 验证所有故障都被正确处理
        successful_handling = sum(1 for r in results if isinstance(r, FailureRecord))
        assert successful_handling == len(faults)

    @pytest.mark.asyncio
    async def test_rapid_failure_sequence(self, fault_injector):
        """测试快速连续故障"""
        recovery_service = get_recovery_service()

        # 1. 快速连续注入和触发故障
        failure_count = 20
        for i in range(failure_count):
            fault_types = [
                FailureType.NETWORK_FAILURE,
                FailureType.TIMEOUT_FAILURE,
                FailureType.EXECUTION_FAILURE,
            ]
            fault_type = random.choice(fault_types)

            if fault_type == FailureType.NETWORK_FAILURE:
                fault = fault_injector.inject_network_failure(
                    f"node-rapid-{i}", FailureSeverity.MEDIUM
                )
            elif fault_type == FailureType.TIMEOUT_FAILURE:
                fault = fault_injector.inject_timeout_failure(
                    f"op-rapid-{i}", FailureSeverity.MEDIUM
                )
            else:
                fault = fault_injector.inject_execution_failure(
                    f"task-rapid-{i}", FailureSeverity.HIGH
                )

            # 触发并处理故障
            try:
                fault_injector.trigger_fault(fault["fault_id"])
            except (ConnectionError, TimeoutError, RuntimeError) as e:
                failure = await recovery_service.handle_failure(
                    task_id=f"task-rapid-{i}",
                    failure_type=fault_type,
                    severity=FailureSeverity.MEDIUM,
                    error_message=str(e),
                    auto_process=False,
                )

                # 验证故障被正确记录
                assert failure.failure_id is not None

        # 2. 验证故障统计
        failures = recovery_service.rollback_service.list_failure_records(limit=100)
        assert len(failures) >= failure_count


class TestFaultRecoveryScenarios:
    """实际故障恢复场景测试"""

    @pytest.mark.asyncio
    async def test_complete_rollback_scenario(self):
        """测试完整的回滚场景"""
        rollback_service = get_rollback_service()

        # 1. 模拟一个配置变更失败的场景
        original_config = {"version": "1.0", "feature_enabled": False}
        new_config = {"version": "2.0", "feature_enabled": True}

        # 2. 创建配置变更失败
        failure = rollback_service.create_failure_record(
            task_id="task-config-change",
            failure_type=FailureType.CONFIGURATION_ERROR,
            severity=FailureSeverity.HIGH,
            error_message="新配置导致服务启动失败",
            context={
                "config_change": {"from": original_config, "to": new_config},
                "impact": "service_unavailable",
            },
        )

        # 3. 创建回滚计划
        rollback_plan = rollback_service.create_rollback_plan(
            name="配置变更回滚",
            description="回滚失败的配置变更",
            trigger_reason=failure.error_message,
            trigger_type="auto",
            triggered_by="system",
            rollback_type=RollbackType.CONFIG,
            target_resources=["/etc/app/config.json"],
            original_task_id=failure.task_id,
            estimated_duration_seconds=300,
        )

        # 4. 验证回滚计划内容
        assert len(rollback_plan.steps) > 0
        assert any("backup" in step.operation.lower() for step in rollback_plan.steps)
        assert any("restore" in step.operation.lower() for step in rollback_plan.steps)

    @pytest.mark.asyncio
    async def test_service_degradation_scenario(self):
        """测试服务降级场景"""
        recovery_service = get_recovery_service()

        # 1. 模拟服务性能降级
        performance_degradation_failure = await recovery_service.handle_failure(
            task_id="task-service-001",
            failure_type=FailureType.RESOURCE_EXHAUSTION,
            severity=FailureSeverity.MEDIUM,
            error_message="CPU使用率过高，服务性能下降",
            context={"cpu_usage": 95.0, "memory_usage": 85.0, "response_time_ms": 5000},
            auto_process=False,
        )

        # 2. 验证恢复策略
        assert performance_degradation_failure.recovery_action in [
            RecoveryAction.ESCALATE,
            RecoveryAction.MANUAL_INTERVENTION,
        ]

    @pytest.mark.asyncio
    async def test_partial_failure_scenario(self):
        """测试部分失败场景"""
        rollback_service = get_rollback_service()

        # 1. 模拟批量操作中的部分失败
        partial_failure = rollback_service.create_failure_record(
            task_id="task-batch-001",
            failure_type=FailureType.EXECUTION_FAILURE,
            severity=FailureSeverity.MEDIUM,
            error_message="批量操作中部分任务失败",
            context={
                "batch_size": 100,
                "failed_count": 15,
                "success_count": 85,
                "failure_rate": 0.15,
            },
        )

        # 2. 创建针对性恢复计划
        recovery_plan = rollback_service.create_recovery_plan(
            failure_id=partial_failure.failure_id,
            recovery_action=RecoveryAction.RETRY,
            steps=[
                "识别失败的任务",
                "重新执行失败的任务",
                "验证批量操作结果",
                "生成详细报告",
            ],
            validation_criteria=["失败率 < 5%", "总成功率 > 95%"],
            priority=4,
        )

        assert recovery_plan.recovery_action == RecoveryAction.RETRY
        assert len(recovery_plan.steps) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
