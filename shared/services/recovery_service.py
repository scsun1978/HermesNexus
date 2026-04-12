"""
HermesNexus Phase 3 - 故障恢复服务
实现故障检测和自动恢复逻辑
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta, timezone

from shared.models.rollback import (
    FailureRecord,
    RecoveryPlan,
    RecoveryAction,
    FailureType,
    FailureSeverity,
)
from shared.services.rollback_service import get_rollback_service

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RecoveryServiceConfig:
    """恢复服务配置"""

    def __init__(
        self,
        auto_recovery_enabled: bool = True,
        max_concurrent_recoveries: int = 3,
        recovery_timeout_seconds: int = 600,
        notification_enabled: bool = True,
        escalation_enabled: bool = True,
    ):
        self.auto_recovery_enabled = auto_recovery_enabled
        self.max_concurrent_recoveries = max_concurrent_recoveries
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.notification_enabled = notification_enabled
        self.escalation_enabled = escalation_enabled


class RecoveryService:
    """故障恢复服务 - 故障检测和恢复核心逻辑"""

    def __init__(self, config: Optional[RecoveryServiceConfig] = None):
        """
        初始化恢复服务

        Args:
            config: 恢复服务配置
        """
        self.config = config or RecoveryServiceConfig()

        # 获取回滚服务
        self.rollback_service = get_rollback_service()

        # 恢复任务队列
        self._recovery_queue: asyncio.Queue = None

        # 执行中的恢复任务
        self._active_recoveries: Dict[str, asyncio.Task] = {}

        # 恢复处理器映射
        self._recovery_handlers = {
            RecoveryAction.RETRY: self._handle_retry,
            RecoveryAction.ROLLBACK: self._handle_rollback,
            RecoveryAction.SKIP: self._handle_skip,
            RecoveryAction.ESCALATE: self._handle_escalate,
            RecoveryAction.MANUAL_INTERVENTION: self._handle_manual_intervention,
            RecoveryAction.IGNORE: self._handle_ignore,
        }

        # 故障检测器
        self._failure_detectors: List[Callable] = []

    async def start(self):
        """启动恢复服务"""
        if self._recovery_queue is None:
            self._recovery_queue = asyncio.Queue()

        # 启动恢复处理任务
        for i in range(self.config.max_concurrent_recoveries):
            asyncio.create_task(self._recovery_worker(i))

        logger.info("恢复服务已启动")

    async def stop(self):
        """停止恢复服务"""
        # 取消所有执行中的恢复任务
        for task_id, task in self._active_recoveries.items():
            task.cancel()

        # 等待任务结束
        if self._active_recoveries:
            await asyncio.gather(
                *self._active_recoveries.values(), return_exceptions=True
            )

        logger.info("恢复服务已停止")

    async def _recovery_worker(self, worker_id: int):
        """恢复工作协程"""
        logger.info(f"恢复工作协程 {worker_id} 已启动")

        while True:
            try:
                # 从队列获取恢复任务
                recovery_plan = await self._recovery_queue.get()

                logger.info(
                    f"工作协程 {worker_id} 开始处理恢复计划: {recovery_plan.plan_id}"
                )

                # 处理恢复计划
                await self._process_recovery_plan(recovery_plan)

                self._recovery_queue.task_done()

            except asyncio.CancelledError:
                logger.info(f"恢复工作协程 {worker_id} 已取消")
                break
            except Exception as e:
                logger.error(f"恢复工作协程 {worker_id} 处理失败: {str(e)}")

    async def handle_failure(
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
        auto_process: bool = True,
    ) -> FailureRecord:
        """
        处理故障

        Args:
            task_id: 关联任务ID
            failure_type: 故障类型
            severity: 严重程度
            error_message: 错误消息
            node_id: 关联节点ID
            asset_id: 关联资产ID
            stack_trace: 错误堆栈
            context: 故障上下文
            auto_process: 是否自动处理

        Returns:
            故障记录对象
        """
        # 创建故障记录
        failure = self.rollback_service.create_failure_record(
            task_id=task_id,
            failure_type=failure_type,
            severity=severity,
            error_message=error_message,
            node_id=node_id,
            asset_id=asset_id,
            stack_trace=stack_trace,
            context=context,
            metadata=metadata,
        )

        logger.info(
            f"记录故障: {failure.failure_id}, 类型: {failure_type.value}, 严重程度: {severity.value}"
        )

        # 如果启用自动处理且允许自动恢复
        if auto_process and self.config.auto_recovery_enabled:
            await self._auto_handle_failure(failure)

        return failure

    async def _auto_handle_failure(self, failure: FailureRecord):
        """自动处理故障"""
        try:
            # 创建恢复计划
            recovery_plan = await self._create_auto_recovery_plan(failure)

            if recovery_plan:
                # 将恢复计划加入队列
                await self._recovery_queue.put(recovery_plan)
                logger.info(f"恢复计划已加入队列: {recovery_plan.plan_id}")

        except Exception as e:
            logger.error(f"自动处理故障失败: {str(e)}")

    async def _create_auto_recovery_plan(
        self, failure: FailureRecord
    ) -> Optional[RecoveryPlan]:
        """创建自动恢复计划"""
        # 根据故障类型和严重程度确定恢复策略
        recovery_action = failure.recovery_action

        # 生成恢复步骤和验证标准
        steps, validation_criteria = self._generate_recovery_steps(
            failure, recovery_action
        )

        # 创建恢复计划
        plan = self.rollback_service.create_recovery_plan(
            failure_id=failure.failure_id,
            recovery_action=recovery_action,
            steps=steps,
            validation_criteria=validation_criteria,
            priority=self._calculate_priority(failure),
        )

        return plan

    def _generate_recovery_steps(
        self, failure: FailureRecord, recovery_action: RecoveryAction
    ) -> tuple[List[str], List[str]]:
        """生成恢复步骤和验证标准"""
        steps = []
        validation_criteria = []

        if recovery_action == RecoveryAction.RETRY:
            steps = [
                "检查故障条件是否仍然存在",
                "清除错误状态",
                f"重试任务 {failure.task_id}",
                "验证执行结果",
            ]
            validation_criteria = ["任务执行成功", "无错误日志"]

        elif recovery_action == RecoveryAction.ROLLBACK:
            steps = [
                "识别受影响的资源和变更",
                "创建回滚计划",
                "执行回滚操作",
                "验证回滚结果",
                "通知相关人员",
            ]
            validation_criteria = ["系统状态恢复正常", "服务可访问"]

        elif recovery_action == RecoveryAction.SKIP:
            steps = [
                "评估跳过该操作的影响",
                "标记操作为已跳过",
                "继续执行后续步骤",
                "记录跳过原因",
            ]
            validation_criteria = ["后续步骤能正常执行"]

        elif recovery_action == RecoveryAction.ESCALATE:
            steps = [
                "收集故障详细信息",
                "评估升级级别",
                "通知上级处理人员",
                "提供故障上下文和建议解决方案",
            ]
            validation_criteria = ["收到处理人员确认"]

        elif recovery_action == RecoveryAction.MANUAL_INTERVENTION:
            steps = [
                "暂停自动化操作",
                "收集和记录故障信息",
                "通知操作人员",
                "等待人工处理",
                "记录处理结果",
            ]
            validation_criteria = ["操作人员确认问题已解决"]

        elif recovery_action == RecoveryAction.IGNORE:
            steps = [
                "评估忽略该故障的风险",
                "记录忽略原因",
                "添加监控标记",
                "继续正常操作",
            ]
            validation_criteria = ["系统能继续正常运行"]

        return steps, validation_criteria

    def _calculate_priority(self, failure: FailureRecord) -> int:
        """计算恢复优先级"""
        # 基础优先级基于严重程度
        priority_map = {
            FailureSeverity.LOW: 8,
            FailureSeverity.MEDIUM: 5,
            FailureSeverity.HIGH: 3,
            FailureSeverity.CRITICAL: 1,
        }

        priority = priority_map.get(failure.severity, 5)

        # 根据故障类型调整优先级
        if failure.failure_type in [
            FailureType.APPROVAL_REJECTED,
            FailureType.CONFIGURATION_ERROR,
        ]:
            priority = max(1, priority - 1)  # 提高优先级
        elif failure.failure_type == FailureType.NETWORK_FAILURE:
            priority = min(10, priority + 1)  # 降低优先级

        return priority

    async def _process_recovery_plan(self, recovery_plan: RecoveryPlan):
        """处理恢复计划"""
        plan_id = recovery_plan.plan_id
        failure = self.rollback_service.get_failure_record(recovery_plan.failure_id)

        if not failure:
            logger.error(f"故障不存在: {recovery_plan.failure_id}")
            return

        logger.info(f"开始处理恢复计划: {plan_id}")

        try:
            # 更新恢复计划状态
            recovery_plan.status = "executing"
            recovery_plan.started_at = datetime.now(timezone.utc)

            # 获取对应的恢复处理器
            handler = self._recovery_handlers.get(recovery_plan.recovery_action)
            if not handler:
                raise Exception(f"不支持的恢复动作: {recovery_plan.recovery_action}")

            # 执行恢复处理
            result = await handler(failure, recovery_plan)

            # 更新恢复计划状态
            recovery_plan.status = "completed"
            recovery_plan.completed_at = datetime.now(timezone.utc)
            recovery_plan.success = result.get("success", False)
            recovery_plan.result_message = result.get("message", "")

            # 更新故障记录
            failure.recovery_status = "completed"
            failure.recovery_result = recovery_plan.result_message
            failure.recovered_at = datetime.now(timezone.utc)

            logger.info(f"恢复计划完成: {plan_id}, 成功: {recovery_plan.success}")

        except Exception as e:
            # 恢复失败
            recovery_plan.status = "failed"
            recovery_plan.completed_at = datetime.now(timezone.utc)
            recovery_plan.success = False
            recovery_plan.result_message = f"恢复失败: {str(e)}"

            failure.recovery_status = "failed"
            failure.recovery_result = str(e)

            logger.error(f"恢复计划失败: {plan_id}, 错误: {str(e)}")

    async def _handle_retry(
        self, failure: FailureRecord, recovery_plan: RecoveryPlan
    ) -> Dict[str, Any]:
        """处理重试恢复"""
        logger.info(f"执行重试恢复: {failure.task_id}")

        # 模拟重试逻辑
        await asyncio.sleep(2)

        # 在实际实现中，这里应该：
        # 1. 检查任务状态
        # 2. 清除错误状态
        # 3. 重新执行任务
        # 4. 验证执行结果

        success = True  # 模拟成功
        message = f"任务 {failure.task_id} 重试成功"

        return {"success": success, "message": message}

    async def _handle_rollback(
        self, failure: FailureRecord, recovery_plan: RecoveryPlan
    ) -> Dict[str, Any]:
        """处理回滚恢复"""
        logger.info(f"执行回滚恢复: {failure.task_id}")

        # 创建自动回滚计划
        rollback_plan = self.rollback_service.create_rollback_plan(
            name=f"自动回滚 - {failure.task_id}",
            description=f"因{failure.failure_type.value}故障触发的自动回滚",
            trigger_reason=failure.error_message,
            trigger_type="auto",
            triggered_by="system",
            rollback_type=self._determine_rollback_type(failure),
            target_resources=[failure.asset_id] if failure.asset_id else [],
            original_task_id=failure.task_id,
            estimated_duration_seconds=300,
        )

        # 执行回滚
        result_plan = await self.rollback_service.execute_rollback_plan(
            rollback_plan.plan_id, auto_confirm=True
        )

        success = result_plan.status.value == "completed"
        message = f"回滚 {rollback_plan.plan_id} {'成功' if success else '失败'}"

        return {"success": success, "message": message}

    def _determine_rollback_type(self, failure: FailureRecord):
        """根据故障确定回滚类型"""
        if failure.failure_type == FailureType.CONFIGURATION_ERROR:
            from shared.models.rollback import RollbackType

            return RollbackType.CONFIG
        elif failure.failure_type in [
            FailureType.EXECUTION_FAILURE,
            FailureType.TIMEOUT_FAILURE,
        ]:
            from shared.models.rollback import RollbackType

            return RollbackType.SERVICE
        else:
            from shared.models.rollback import RollbackType

            return RollbackType.TASK

    async def _handle_skip(
        self, failure: FailureRecord, recovery_plan: RecoveryPlan
    ) -> Dict[str, Any]:
        """处理跳过恢复"""
        logger.info(f"执行跳过恢复: {failure.task_id}")

        # 模拟跳过逻辑
        await asyncio.sleep(1)

        success = True
        message = f"任务 {failure.task_id} 已跳过，继续后续操作"

        return {"success": success, "message": message}

    async def _handle_escalate(
        self, failure: FailureRecord, recovery_plan: RecoveryPlan
    ) -> Dict[str, Any]:
        """处理升级恢复"""
        logger.info(f"执行升级恢复: {failure.task_id}")

        # 确定升级级别
        escalation_level = self._determine_escalation_level(failure)

        # 发送通知
        await self._send_escalation_notification(failure, escalation_level)

        success = True
        message = f"故障已升级到 {escalation_level} 级别处理"

        return {"success": success, "message": message}

    def _determine_escalation_level(self, failure: FailureRecord) -> str:
        """确定升级级别"""
        if failure.severity == FailureSeverity.CRITICAL:
            return "super_admin"
        elif failure.severity == FailureSeverity.HIGH:
            return "admin"
        else:
            return "operator"

    async def _send_escalation_notification(self, failure: FailureRecord, level: str):
        """发送升级通知"""
        # 在实际实现中，这里应该发送邮件、短信或其他通知
        logger.info(f"发送升级通知: 故障 {failure.failure_id}, 级别 {level}")
        await asyncio.sleep(0.5)  # 模拟发送通知

    async def _handle_manual_intervention(
        self, failure: FailureRecord, recovery_plan: RecoveryPlan
    ) -> Dict[str, Any]:
        """处理人工介入恢复"""
        logger.info(f"执行人工介入恢复: {failure.task_id}")

        # 暂停自动化操作
        # 通知操作人员
        await self._send_manual_intervention_notification(failure)

        success = True
        message = "已暂停自动化操作，等待人工处理"

        return {"success": success, "message": message}

    async def _send_manual_intervention_notification(self, failure: FailureRecord):
        """发送人工介入通知"""
        logger.info(f"发送人工介入通知: 故障 {failure.failure_id}")
        await asyncio.sleep(0.5)  # 模拟发送通知

    async def _handle_ignore(
        self, failure: FailureRecord, recovery_plan: RecoveryPlan
    ) -> Dict[str, Any]:
        """处理忽略恢复"""
        logger.info(f"执行忽略恢复: {failure.task_id}")

        # 评估忽略风险
        risk_assessment = await self._assess_ignore_risk(failure)

        if risk_assessment["safe_to_ignore"]:
            # 记录忽略原因
            await self._log_ignore_reason(failure, risk_assessment["reason"])

            success = True
            message = f"故障已忽略: {risk_assessment['reason']}"
        else:
            success = False
            message = f"故障不能忽略: {risk_assessment['reason']}"

        return {"success": success, "message": message}

    async def _assess_ignore_risk(self, failure: FailureRecord) -> Dict[str, Any]:
        """评估忽略风险"""
        # 简化的风险评估逻辑
        if failure.severity == FailureSeverity.LOW:
            return {"safe_to_ignore": True, "reason": "低风险故障，影响有限"}
        else:
            return {"safe_to_ignore": False, "reason": "故障严重程度较高，不能忽略"}

    async def _log_ignore_reason(self, failure: FailureRecord, reason: str):
        """记录忽略原因"""
        logger.info(f"记录忽略原因: 故障 {failure.failure_id}, 原因: {reason}")
        await asyncio.sleep(0.1)  # 模拟记录操作

    def register_failure_detector(self, detector: Callable):
        """
        注册故障检测器

        Args:
            detector: 故障检测器函数，签名为 async def detector() -> List[Dict]
        """
        self._failure_detectors.append(detector)
        logger.info(f"已注册故障检测器: {detector.__name__}")

    async def run_failure_detection(self):
        """运行故障检测"""
        detected_failures = []

        for detector in self._failure_detectors:
            try:
                failures = await detector()
                detected_failures.extend(failures)
            except Exception as e:
                logger.error(f"故障检测器执行失败: {detector.__name__}, 错误: {str(e)}")

        # 处理检测到的故障
        for failure_info in detected_failures:
            try:
                await self.handle_failure(**failure_info)
            except Exception as e:
                logger.error(f"处理检测到的故障失败: {str(e)}")

        return detected_failures

    async def get_recovery_status(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """获取恢复状态"""
        plan = self.rollback_service.get_recovery_plan(plan_id)
        if not plan:
            return None

        return {
            "plan_id": plan.plan_id,
            "status": plan.status,
            "recovery_action": plan.recovery_action.value,
            "success": plan.success,
            "result_message": plan.result_message,
            "created_at": plan.created_at,
            "started_at": plan.started_at,
            "completed_at": plan.completed_at,
        }


# 全局恢复服务实例（延迟初始化）
_global_recovery_service: Optional[RecoveryService] = None


def get_recovery_service() -> RecoveryService:
    """获取全局恢复服务实例"""
    global _global_recovery_service
    if _global_recovery_service is None:
        _global_recovery_service = RecoveryService()
    return _global_recovery_service


def create_recovery_service(config: RecoveryServiceConfig) -> RecoveryService:
    """
    创建自定义恢复服务

    Args:
        config: 恢复服务配置

    Returns:
        恢复服务实例
    """
    return RecoveryService(config=config)
