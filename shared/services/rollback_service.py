"""
HermesNexus Phase 3 - 回滚服务
实现回滚流程的核心业务逻辑
"""

import uuid
import json
import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from shared.models.rollback import (
    RollbackPlan,
    RollbackStep,
    RollbackType,
    RollbackStatus,
    RollbackStatistics,
    FailureRecord,
    RecoveryPlan,
    FailureType,
    FailureSeverity,
    RecoveryAction,
)


class RollbackServiceConfig:
    """回滚服务配置"""

    def __init__(
        self,
        config_dir: str = "config",
        default_timeout_seconds: int = 300,
        default_max_retries: int = 3,
        parallel_execution: bool = False,
        auto_rollback_on_failure: bool = True,
        require_confirmation: bool = True,
        simulate_execution_success_rate: float = 1.0,
        simulate_validation_success_rate: float = 1.0,
    ):
        self.config_dir = Path(config_dir)
        self.default_timeout_seconds = default_timeout_seconds
        self.default_max_retries = default_max_retries
        self.parallel_execution = parallel_execution
        self.auto_rollback_on_failure = auto_rollback_on_failure
        self.require_confirmation = require_confirmation
        # 模拟执行和验证成功率（用于测试，1.0 = 100%成功）
        self.simulate_execution_success_rate = simulate_execution_success_rate
        self.simulate_validation_success_rate = simulate_validation_success_rate


class RollbackService:
    """回滚服务 - 回滚流程核心逻辑"""

    def __init__(self, config: Optional[RollbackServiceConfig] = None):
        """
        初始化回滚服务

        Args:
            config: 回滚服务配置
        """
        self.config = config or RollbackServiceConfig()

        # 回滚计划存储（生产环境应使用数据库）
        self._plans: Dict[str, RollbackPlan] = {}

        # 故障记录存储
        self._failures: Dict[str, FailureRecord] = {}

        # 恢复计划存储
        self._recovery_plans: Dict[str, RecoveryPlan] = {}

        # 回滚策略配置
        self._strategies = self._load_strategies()

        # 故障处理配置
        self._failure_handlers = self._load_failure_handlers()

        # 执行中的回滚计划（用于并发控制）
        self._executing_plans: Dict[str, asyncio.Task] = {}

    def _load_strategies(self) -> Dict[str, Any]:
        """加载回滚策略配置"""
        strategy_file = self.config.config_dir / "rollback_strategies.json"
        if strategy_file.exists():
            with open(strategy_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("strategies", {})
        return {}

    def _load_failure_handlers(self) -> Dict[str, Any]:
        """加载故障处理配置"""
        handler_file = self.config.config_dir / "failure_handlers.json"
        if handler_file.exists():
            with open(handler_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("handlers", {})
        return {}

    def create_rollback_plan(
        self,
        name: str,
        description: str,
        trigger_reason: str,
        trigger_type: str,
        triggered_by: str,
        rollback_type: RollbackType,
        target_resources: List[str],
        original_task_id: Optional[str] = None,
        original_approval_id: Optional[str] = None,
        priority: int = 5,
        estimated_duration_seconds: int = 300,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RollbackPlan:
        """
        创建回滚计划

        Args:
            name: 回滚计划名称
            description: 回滚计划描述
            trigger_reason: 触发回滚的原因
            trigger_type: 触发类型 (auto/manual)
            triggered_by: 触发人ID
            rollback_type: 回滚类型
            target_resources: 目标资源列表
            original_task_id: 原始任务ID
            original_approval_id: 原始审批ID
            priority: 优先级（1-10）
            estimated_duration_seconds: 预计耗时（秒）
            metadata: 附加元数据

        Returns:
            回滚计划对象
        """
        plan_id = f"rollback-{uuid.uuid4().hex[:8]}"

        # 生成回滚步骤
        steps = self._generate_rollback_steps(
            plan_id=plan_id,
            rollback_type=rollback_type,
            target_resources=target_resources,
        )

        # 估算风险等级
        risk_level = self._estimate_rollback_risk(rollback_type, steps)

        plan = RollbackPlan(
            plan_id=plan_id,
            name=name,
            description=description,
            original_task_id=original_task_id,
            original_approval_id=original_approval_id,
            rollback_type=rollback_type,
            trigger_reason=trigger_reason,
            trigger_type=trigger_type,
            triggered_by=triggered_by,
            triggered_at=datetime.now(timezone.utc),
            steps=steps,
            status=RollbackStatus.PLANNED,
            current_step=0,
            estimated_duration_seconds=estimated_duration_seconds,
            estimated_risk_level=risk_level,
            metadata=metadata or {},
        )

        self._plans[plan_id] = plan
        return plan

    def _generate_rollback_steps(
        self, plan_id: str, rollback_type: RollbackType, target_resources: List[str]
    ) -> List[RollbackStep]:
        """
        生成回滚步骤

        Args:
            plan_id: 计划ID
            rollback_type: 回滚类型
            target_resources: 目标资源列表

        Returns:
            回滚步骤列表
        """
        steps = []

        # 获取该类型的回滚策略
        strategy = self._strategies.get(rollback_type.value, {})
        rollback_order = strategy.get("rollback_order", [])

        for sequence, operation in enumerate(rollback_order, 1):
            step_id = f"{plan_id}-step-{sequence:03d}"

            # 确定目标资源
            target_resource = target_resources[0] if target_resources else "unknown"

            step = RollbackStep(
                step_id=step_id,
                sequence=sequence,
                description=self._get_step_description(operation, rollback_type),
                rollback_type=rollback_type,
                target_resource=target_resource,
                operation=operation,
                parameters=self._get_step_parameters(operation, rollback_type),
                status=RollbackStatus.PLANNED,
                requires_backup=self._requires_backup(operation),
                validation_criteria=strategy.get("validation_steps", []),
            )

            steps.append(step)

        return steps

    def _get_step_description(self, operation: str, rollback_type: RollbackType) -> str:
        """获取步骤描述"""
        descriptions = {
            "backup_current_config": "备份当前配置文件",
            "stop_related_services": "停止相关服务",
            "restore_backup_config": "恢复备份配置",
            "validate_config": "验证配置有效性",
            "start_services": "启动服务",
            "verify_operations": "验证操作结果",
            "backup_current_state": "备份当前状态",
            "stop_current_service": "停止当前服务",
            "restore_previous_version": "恢复上一个版本",
            "update_dependencies": "更新依赖",
            "health_check": "健康检查",
            "backup_device_config": "备份设备配置",
            "disconnect_device": "断开设备连接",
            "restore_firmware_version": "恢复固件版本",
            "restore_device_config": "恢复设备配置",
            "reconnect_device": "重新连接设备",
            "verify_connectivity": "验证连接",
            "test_operations": "测试操作",
            "identify_affected_resources": "识别受影响资源",
            "pause_execution": "暂停执行",
            "compensate_completed_steps": "补偿已完成的步骤",
            "reset_task_status": "重置任务状态",
            "release_resources": "释放资源",
            "notify_stakeholders": "通知相关人员",
            "verify_system_state": "验证系统状态",
        }
        return descriptions.get(operation, f"执行{operation}")

    def _get_step_parameters(
        self, operation: str, rollback_type: RollbackType
    ) -> Dict[str, Any]:
        """获取步骤参数"""
        # 根据操作类型返回不同的参数
        params = {}

        if "backup" in operation:
            params["backup_path"] = (
                f"/backup/{rollback_type.value}/{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            )
        elif "restore" in operation:
            params["backup_path"] = f"/backup/{rollback_type.value}/latest"
        elif "stop" in operation or "start" in operation:
            params["grace_period_seconds"] = 30
            params["force"] = False

        return params

    def _requires_backup(self, operation: str) -> bool:
        """判断操作是否需要备份"""
        backup_operations = ["restore", "deploy", "update", "firmware", "config"]
        return any(op in operation for op in backup_operations)

    def _estimate_rollback_risk(
        self, rollback_type: RollbackType, steps: List[RollbackStep]
    ) -> str:
        """估算回滚风险等级"""
        risk_scores = {
            RollbackType.CONFIG: 2,
            RollbackType.SERVICE: 3,
            RollbackType.DEVICE: 4,
            RollbackType.TASK: 1,
        }

        base_risk = risk_scores.get(rollback_type, 2)

        # 根据步骤数量调整风险
        if len(steps) > 10:
            base_risk += 1

        if base_risk <= 2:
            return "low"
        elif base_risk == 3:
            return "medium"
        else:
            return "high"

    async def execute_rollback_plan(
        self, plan_id: str, auto_confirm: bool = False
    ) -> RollbackPlan:
        """
        执行回滚计划

        Args:
            plan_id: 计划ID
            auto_confirm: 是否自动确认（跳过确认步骤）

        Returns:
            更新后的回滚计划

        Raises:
            ValueError: 计划不存在或状态不允许执行
        """
        plan = self._get_plan(plan_id)

        # 检查状态
        if plan.status not in [RollbackStatus.PLANNED, RollbackStatus.READY]:
            raise ValueError(f"当前状态 {plan.status} 不允许执行")

        # 需要确认
        if self.config.require_confirmation and not auto_confirm:
            plan.status = RollbackStatus.READY
            self._plans[plan_id] = plan
            return plan

        # 开始执行
        plan.status = RollbackStatus.EXECUTING
        plan.started_at = datetime.now(timezone.utc)
        plan.current_step = 0
        self._plans[plan_id] = plan

        try:
            # 执行所有步骤
            for i, step in enumerate(plan.steps):
                plan.current_step = i + 1
                self._plans[plan_id] = plan

                # 执行步骤
                await self._execute_step(plan, step)

                # 检查步骤状态
                if step.status == RollbackStatus.FAILED:
                    # 步骤失败，决定是否继续
                    if step.retry_count < step.max_retries:
                        # 重试
                        step.retry_count += 1
                        await self._execute_step(plan, step)
                    else:
                        # 重试次数用完，回滚失败
                        raise Exception(
                            f"步骤 {step.step_id} 执行失败: {step.error_message}"
                        )

            # 所有步骤成功完成
            plan.status = RollbackStatus.COMPLETED
            plan.completed_at = datetime.now(timezone.utc)
            plan.final_status = "success"
            plan.rollback_summary = f"成功执行 {len(plan.steps)} 个回滚步骤"

        except Exception as e:
            # 回滚执行失败
            plan.status = RollbackStatus.FAILED
            plan.completed_at = datetime.now(timezone.utc)
            plan.final_status = "failed"
            plan.failure_reason = str(e)
            plan.rollback_summary = f"回滚执行失败: {str(e)}"

        finally:
            self._plans[plan_id] = plan

        return plan

    async def _execute_step(self, plan: RollbackPlan, step: RollbackStep):
        """
        执行单个回滚步骤

        Args:
            plan: 回滚计划
            step: 回滚步骤

        Raises:
            Exception: 步骤执行失败
        """
        step.status = RollbackStatus.EXECUTING
        step.executed_at = datetime.now(timezone.utc)

        try:
            # 模拟执行步骤
            await self._simulate_step_execution(step)

            # 验证步骤结果
            if step.validation_criteria:
                await self._validate_step_result(step)

            step.status = RollbackStatus.COMPLETED
            step.result = "执行成功"

        except Exception as e:
            step.status = RollbackStatus.FAILED
            step.error_message = str(e)
            raise

    async def _simulate_step_execution(self, step: RollbackStep):
        """模拟步骤执行（实际实现中应调用具体的执行逻辑）"""
        # 模拟不同操作的执行时间
        execution_times = {
            "backup": 2,
            "restore": 3,
            "stop": 1,
            "start": 2,
            "validate": 1,
            "verify": 1,
            "health_check": 2,
            "test": 3,
        }

        base_time = execution_times.get(step.operation.split("_")[0], 2)
        await asyncio.sleep(base_time)

        # 使用配置的成功率（实际实现中应基于真实执行结果）
        success_rate = self.config.simulate_execution_success_rate
        import random

        if random.random() > success_rate:
            raise Exception(f"步骤执行失败（模拟）: {step.operation}")

    async def _validate_step_result(self, step: RollbackStep):
        """验证步骤执行结果"""
        # 模拟验证逻辑
        await asyncio.sleep(0.5)

        # 使用配置的验证成功率
        success_rate = self.config.simulate_validation_success_rate
        import random

        if random.random() > success_rate:
            raise Exception(f"步骤验证失败: {step.operation}")

    def cancel_rollback_plan(self, plan_id: str) -> RollbackPlan:
        """
        取消回滚计划

        Args:
            plan_id: 计划ID

        Returns:
            更新后的回滚计划

        Raises:
            ValueError: 计划不存在或状态不允许取消
        """
        plan = self._get_plan(plan_id)

        # 只有计划中或就绪状态可以取消
        if plan.status not in [RollbackStatus.PLANNED, RollbackStatus.READY]:
            raise ValueError(f"当前状态 {plan.status.name} 不允许取消")

        plan.status = RollbackStatus.CANCELLED
        plan.completed_at = datetime.now(timezone.utc)
        plan.final_status = "cancelled"
        plan.rollback_summary = "回滚计划已取消"

        self._plans[plan_id] = plan
        return plan

    def get_rollback_plan(self, plan_id: str) -> Optional[RollbackPlan]:
        """
        获取回滚计划

        Args:
            plan_id: 计划ID

        Returns:
            回滚计划对象，如果不存在则返回None
        """
        return self._plans.get(plan_id)

    def list_rollback_plans(
        self,
        status: Optional[RollbackStatus] = None,
        rollback_type: Optional[RollbackType] = None,
        limit: int = 100,
    ) -> List[RollbackPlan]:
        """
        列出回滚计划

        Args:
            status: 状态过滤
            rollback_type: 回滚类型过滤
            limit: 返回数量限制

        Returns:
            回滚计划列表
        """
        plans = list(self._plans.values())

        # 应用过滤条件
        if status:
            plans = [p for p in plans if p.status == status]
        if rollback_type:
            plans = [
                p
                for p in plans
                if any(step.rollback_type == rollback_type for step in p.steps)
            ]

        # 按触发时间倒序排序
        plans.sort(key=lambda x: x.triggered_at, reverse=True)

        return plans[:limit]

    def create_failure_record(
        self,
        task_id: str,
        failure_type: FailureType,
        severity: FailureSeverity,
        error_message: str,
        node_id: Optional[str] = None,
        asset_id: Optional[str] = None,
        stack_trace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FailureRecord:
        """
        创建故障记录

        Args:
            task_id: 关联任务ID
            failure_type: 故障类型
            severity: 严重程度
            error_message: 错误消息
            node_id: 关联节点ID
            asset_id: 关联资产ID
            stack_trace: 错误堆栈
            context: 故障上下文
            metadata: 附加元数据

        Returns:
            故障记录对象
        """
        failure_id = f"failure-{uuid.uuid4().hex[:8]}"

        # 根据故障类型和严重程度确定恢复动作
        recovery_action = self._determine_recovery_action(failure_type, severity)

        failure = FailureRecord(
            failure_id=failure_id,
            task_id=task_id,
            node_id=node_id,
            asset_id=asset_id,
            failure_type=failure_type,
            severity=severity,
            error_message=error_message,
            stack_trace=stack_trace,
            occurred_at=datetime.now(timezone.utc),
            recovery_action=recovery_action,
            recovery_status="pending",
            context=context or {},
            metadata=metadata or {},
        )

        self._failures[failure_id] = failure
        return failure

    def _determine_recovery_action(
        self, failure_type: FailureType, severity: FailureSeverity
    ) -> RecoveryAction:
        """确定恢复动作"""
        handler = self._failure_handlers.get(failure_type.value, {})
        severity_mapping = handler.get("severity_mapping", {})
        severity_config = severity_mapping.get(severity.value, {})

        action_str = severity_config.get("action", "manual_intervention")
        return RecoveryAction(action_str)

    def create_recovery_plan(
        self,
        failure_id: str,
        recovery_action: RecoveryAction,
        steps: List[str],
        validation_criteria: List[str],
        priority: int = 5,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> RecoveryPlan:
        """
        创建恢复计划

        Args:
            failure_id: 关联故障ID
            recovery_action: 恢复动作
            steps: 恢复步骤
            validation_criteria: 验证标准
            priority: 优先级
            name: 恢复计划名称
            description: 恢复计划描述

        Returns:
            恢复计划对象

        Raises:
            ValueError: 故障不存在
        """
        failure = self._get_failure(failure_id)

        plan_id = f"recovery-{uuid.uuid4().hex[:8]}"

        if not name:
            name = f"故障恢复计划 - {failure_id}"
        if not description:
            description = f"针对{failure.failure_type.value}故障的恢复计划"

        plan = RecoveryPlan(
            plan_id=plan_id,
            failure_id=failure_id,
            name=name,
            description=description,
            recovery_action=recovery_action,
            priority=priority,
            steps=steps,
            validation_criteria=validation_criteria,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )

        self._recovery_plans[plan_id] = plan
        return plan

    def get_failure_record(self, failure_id: str) -> Optional[FailureRecord]:
        """获取故障记录"""
        return self._failures.get(failure_id)

    def get_recovery_plan(self, plan_id: str) -> Optional[RecoveryPlan]:
        """获取恢复计划"""
        return self._recovery_plans.get(plan_id)

    def list_failure_records(
        self,
        task_id: Optional[str] = None,
        failure_type: Optional[FailureType] = None,
        severity: Optional[FailureSeverity] = None,
        limit: int = 100,
    ) -> List[FailureRecord]:
        """列出故障记录"""
        failures = list(self._failures.values())

        # 应用过滤条件
        if task_id:
            failures = [f for f in failures if f.task_id == task_id]
        if failure_type:
            failures = [f for f in failures if f.failure_type == failure_type]
        if severity:
            failures = [f for f in failures if f.severity == severity]

        # 按发生时间倒序排序
        failures.sort(key=lambda x: x.occurred_at, reverse=True)

        return failures[:limit]

    def get_statistics(self) -> RollbackStatistics:
        """获取回滚统计信息"""
        plans = list(self._plans.values())

        # 基础统计
        total = len(plans)
        successful = sum(1 for p in plans if p.status == RollbackStatus.COMPLETED)
        failed = sum(1 for p in plans if p.status == RollbackStatus.FAILED)
        cancelled = sum(1 for p in plans if p.status == RollbackStatus.CANCELLED)

        # 分类统计
        by_type = {}
        by_trigger = {}

        for plan in plans:
            for step in plan.steps:
                type_str = step.rollback_type.value
                by_type[type_str] = by_type.get(type_str, 0) + 1

            trigger_str = plan.trigger_type
            by_trigger[trigger_str] = by_trigger.get(trigger_str, 0) + 1

        # 时间统计
        durations = []
        for plan in plans:
            if plan.started_at and plan.completed_at:
                duration = (plan.completed_at - plan.started_at).total_seconds()
                durations.append(duration)

        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
        else:
            avg_duration = 0.0
            max_duration = 0.0
            min_duration = 0.0

        # 成功率
        completed = successful + failed
        success_rate = successful / completed if completed > 0 else 0.0

        return RollbackStatistics(
            total_rollback_plans=total,
            successful_rollbacks=successful,
            failed_rollbacks=failed,
            cancelled_rollbacks=cancelled,
            by_type=by_type,
            by_trigger=by_trigger,
            avg_duration_seconds=avg_duration,
            max_duration_seconds=max_duration,
            min_duration_seconds=min_duration,
            success_rate=success_rate,
        )

    def _get_plan(self, plan_id: str) -> RollbackPlan:
        """获取回滚计划（不存在时抛出异常）"""
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"回滚计划不存在: {plan_id}")
        return plan

    def _get_failure(self, failure_id: str) -> FailureRecord:
        """获取故障记录（不存在时抛出异常）"""
        failure = self._failures.get(failure_id)
        if not failure:
            raise ValueError(f"故障记录不存在: {failure_id}")
        return failure


# 全局回滚服务实例（延迟初始化）
_global_rollback_service: Optional[RollbackService] = None


def get_rollback_service() -> RollbackService:
    """获取全局回滚服务实例"""
    global _global_rollback_service
    if _global_rollback_service is None:
        _global_rollback_service = RollbackService()
    return _global_rollback_service


def create_rollback_service(config: RollbackServiceConfig) -> RollbackService:
    """
    创建自定义回滚服务

    Args:
        config: 回滚服务配置

    Returns:
        回滚服务实例
    """
    return RollbackService(config=config)
