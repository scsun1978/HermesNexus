"""
HermesNexus 审计回放服务
Audit Replay Service - 实现审计日志的回放功能
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum
import uuid
import json

from shared.models.audit import AuditLog, AuditAction, AuditCategory
from shared.services.audit_service import AuditService


class ReplayMode(str, Enum):
    """回放模式"""

    SIMULATION = "simulation"  # 模拟回放：只展示步骤，不实际执行
    VALIDATION = "validation"  # 验证回放：验证是否可以重新执行
    EXECUTION = "execution"  # 实际回放：真正重新执行操作


class ReplayResult(str, Enum):
    """回放结果"""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class AuditReplayService:
    """审计回放服务"""

    def __init__(self, audit_service: AuditService = None):
        """
        初始化审计回放服务

        Args:
            audit_service: 审计服务实例
        """
        self.audit_service = audit_service

    def replay_audit_log(
        self,
        audit_id: str,
        mode: ReplayMode = ReplayMode.SIMULATION,
        actor: str = "system",
        overrides: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        回放审计日志

        Args:
            audit_id: 审计日志ID
            mode: 回放模式
            actor: 执行回放的用户
            overrides: 参数覆盖（用于调整回放时的参数）

        Returns:
            回放结果字典
        """
        # 获取原始审计日志
        if self.audit_service:
            original_audit = self.audit_service.get_audit_log(audit_id)
            if not original_audit:
                return {
                    "success": False,
                    "error": "审计日志不存在",
                    "audit_id": audit_id,
                    "replay_id": None,
                }
        else:
            # 如果没有审计服务，创建一个模拟的审计日志对象用于测试
            return {
                "success": False,
                "error": "审计服务未初始化",
                "audit_id": audit_id,
                "replay_id": None,
            }

        # 检查是否支持回放
        replay_capability = self._check_replay_capability(original_audit)
        if not replay_capability["can_replay"]:
            return {
                "success": False,
                "error": replay_capability["reason"],
                "audit_id": audit_id,
                "replay_id": None,
            }

        # 创建回放记录
        replay_id = f"replay-{uuid.uuid4().hex[:8]}"

        try:
            # 根据回放模式执行
            if mode == ReplayMode.SIMULATION:
                result = self._simulation_replay(original_audit, overrides)
            elif mode == ReplayMode.VALIDATION:
                result = self._validation_replay(original_audit, overrides)
            elif mode == ReplayMode.EXECUTION:
                result = self._execution_replay(original_audit, overrides)
            else:
                raise ValueError(f"不支持的回放模式: {mode}")

            # 记录回放操作
            self._log_replay_action(
                replay_id=replay_id,
                original_audit=original_audit,
                mode=mode,
                actor=actor,
                result=result,
            )

            return {
                "success": True,
                "replay_id": replay_id,
                "audit_id": audit_id,
                "mode": mode.value,
                "original_action": original_audit.action.value,
                "result": result,
            }

        except Exception as e:
            # 记录回放失败
            self._log_replay_action(
                replay_id=replay_id,
                original_audit=original_audit,
                mode=mode,
                actor=actor,
                result={"status": "error", "error": str(e)},
            )

            return {
                "success": False,
                "error": str(e),
                "audit_id": audit_id,
                "replay_id": replay_id,
            }

    def _check_replay_capability(self, audit_log: AuditLog) -> Dict[str, Any]:
        """
        检查审计日志是否支持回放

        Args:
            audit_log: 审计日志

        Returns:
            检查结果字典
        """
        # 不支持回放的操作类型
        non_replayable_actions = [
            AuditAction.AUDIT_LOG_VIEWED,
            AuditAction.AUTH_DENIED,  # 认证失败不支持回放
            AuditAction.AUTH_SUCCESS,  # 认证成功不支持回放
        ]

        if audit_log.action in non_replayable_actions:
            return {
                "can_replay": False,
                "reason": f"操作类型 {audit_log.action.value} 不支持回放",
            }

        # 检查是否有足够的信息进行回放
        if not audit_log.details:
            return {
                "can_replay": False,
                "reason": "缺少详细信息，无法回放",
            }

        # 检查目标是否仍然存在
        if audit_log.target_type and audit_log.target_id:
            # 这里可以添加更复杂的检查逻辑
            # 例如检查目标节点/设备是否仍然存在
            pass

        return {"can_replay": True, "reason": None}

    def _simulation_replay(
        self, audit_log: AuditLog, overrides: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        模拟回放：只展示步骤，不实际执行

        Args:
            audit_log: 原始审计日志
            overrides: 参数覆盖

        Returns:
            回放结果
        """
        steps = self._generate_replay_steps(audit_log, overrides)

        return {
            "status": ReplayResult.SUCCESS,
            "mode": ReplayMode.SIMULATION,
            "message": f"模拟回放完成，共 {len(steps)} 个步骤",
            "steps": steps,
            "estimated_duration_seconds": self._estimate_duration(steps),
        }

    def _validation_replay(
        self, audit_log: AuditLog, overrides: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        验证回放：验证是否可以重新执行

        Args:
            audit_log: 原始审计日志
            overrides: 参数覆盖

        Returns:
            验证结果
        """
        validation_issues = []
        warnings = []

        # 生成回放步骤
        steps = self._generate_replay_steps(audit_log, overrides)

        # 验证每个步骤
        for step in steps:
            # 检查依赖项
            if "dependencies" in step:
                for dep in step["dependencies"]:
                    if not self._check_dependency(dep):
                        validation_issues.append(f"步骤 {step['step_number']} 依赖项 {dep} 不可用")

            # 检查参数有效性
            if "parameters" in step:
                for param_name, param_value in step["parameters"].items():
                    if param_value is None:
                        warnings.append(f"步骤 {step['step_number']} 参数 {param_name} 为空")

        # 判断验证结果
        if validation_issues:
            result_status = ReplayResult.FAILED
            message = f"验证失败，发现 {len(validation_issues)} 个问题"
        elif warnings:
            result_status = ReplayResult.SUCCESS
            message = f"验证通过，但有 {len(warnings)} 个警告"
        else:
            result_status = ReplayResult.SUCCESS
            message = "验证通过，可以执行回放"

        return {
            "status": result_status,
            "mode": ReplayMode.VALIDATION,
            "message": message,
            "steps": steps,
            "validation_issues": validation_issues,
            "warnings": warnings,
            "can_execute": len(validation_issues) == 0,
        }

    def _execution_replay(
        self, audit_log: AuditLog, overrides: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        实际回放：真正重新执行操作

        Args:
            audit_log: 原始审计日志
            overrides: 参数覆盖

        Returns:
            执行结果
        """
        # 首先进行验证
        validation_result = self._validation_replay(audit_log, overrides)
        if not validation_result["can_execute"]:
            return {
                "status": ReplayResult.FAILED,
                "mode": ReplayMode.EXECUTION,
                "message": "验证失败，无法执行回放",
                "validation_result": validation_result,
            }

        executed_steps = []
        failed_steps = []

        try:
            # 执行每个步骤
            steps = self._generate_replay_steps(audit_log, overrides)
            for step in steps:
                try:
                    step_result = self._execute_step(step, overrides)
                    executed_steps.append(
                        {"step": step, "result": step_result, "status": "success"}
                    )
                except Exception as e:
                    failed_steps.append({"step": step, "error": str(e), "status": "failed"})

                    # 根据失败策略决定是否继续
                    if step.get("stop_on_error", True):
                        break

            # 确定最终结果
            if failed_steps:
                if executed_steps:
                    result_status = ReplayResult.PARTIAL
                    message = f"部分成功：{len(executed_steps)} 个步骤成功，{len(failed_steps)} 个步骤失败"
                else:
                    result_status = ReplayResult.FAILED
                    message = f"执行失败：所有步骤都失败"
            else:
                result_status = ReplayResult.SUCCESS
                message = f"执行成功：共 {len(executed_steps)} 个步骤"

            return {
                "status": result_status,
                "mode": ReplayMode.EXECUTION,
                "message": message,
                "executed_steps": executed_steps,
                "failed_steps": failed_steps,
                "execution_time": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            return {
                "status": ReplayResult.FAILED,
                "mode": ReplayMode.EXECUTION,
                "message": f"执行失败：{str(e)}",
                "executed_steps": executed_steps,
                "failed_steps": failed_steps,
            }

    def _generate_replay_steps(
        self, audit_log: AuditLog, overrides: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        生成回放步骤

        Args:
            audit_log: 审计日志
            overrides: 参数覆盖

        Returns:
            回放步骤列表
        """
        overrides = overrides or {}
        details = audit_log.details or {}

        # 根据操作类型生成不同的步骤
        if audit_log.action == AuditAction.TASK_CREATED:
            return self._generate_task_creation_steps(audit_log, overrides)
        elif audit_log.action == AuditAction.ASSET_REGISTERED:
            return self._generate_asset_creation_steps(audit_log, overrides)
        elif audit_log.action == AuditAction.ASSET_UPDATED:
            return self._generate_asset_update_steps(audit_log, overrides)
        elif audit_log.action == AuditAction.NODE_REGISTERED:
            return self._generate_node_registration_steps(audit_log, overrides)
        else:
            # 通用步骤生成
            return [
                {
                    "step_number": 1,
                    "action": audit_log.action.value,
                    "description": audit_log.message,
                    "target_type": audit_log.target_type,
                    "target_id": audit_log.target_id,
                    "parameters": {**details, **overrides},
                    "dependencies": self._extract_dependencies(audit_log),
                }
            ]

    def _generate_task_creation_steps(
        self, audit_log: AuditLog, overrides: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成任务创建的回放步骤"""
        details = audit_log.details or {}

        return [
            {
                "step_number": 1,
                "action": "validate_device",
                "description": "验证目标设备",
                "target_id": details.get("target_device_id"),
                "parameters": {"device_id": details.get("target_device_id")},
                "dependencies": ["device_exists"],
            },
            {
                "step_number": 2,
                "action": "validate_node",
                "description": "验证目标节点",
                "target_id": overrides.get("node_id") or details.get("node_id"),
                "parameters": {"node_id": overrides.get("node_id") or details.get("node_id")},
                "dependencies": ["node_exists"],
            },
            {
                "step_number": 3,
                "action": "create_task",
                "description": "创建任务",
                "parameters": {
                    **details,
                    **overrides,
                },
                "dependencies": ["device_exists", "node_exists"],
                "stop_on_error": True,
            },
        ]

    def _generate_asset_creation_steps(
        self, audit_log: AuditLog, overrides: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成资产创建的回放步骤"""
        details = audit_log.details or {}

        return [
            {
                "step_number": 1,
                "action": "validate_asset_parameters",
                "description": "验证资产参数",
                "parameters": {**details, **overrides},
                "dependencies": [],
            },
            {
                "step_number": 2,
                "action": "create_asset",
                "description": "创建资产",
                "parameters": {
                    **details,
                    **overrides,
                },
                "dependencies": ["parameters_valid"],
                "stop_on_error": True,
            },
        ]

    def _generate_asset_update_steps(
        self, audit_log: AuditLog, overrides: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成资产更新的回放步骤"""
        details = audit_log.details or {}

        return [
            {
                "step_number": 1,
                "action": "validate_asset_exists",
                "description": "验证资产存在",
                "target_id": audit_log.target_id,
                "parameters": {"asset_id": audit_log.target_id},
                "dependencies": [],
            },
            {
                "step_number": 2,
                "action": "validate_update_parameters",
                "description": "验证更新参数",
                "parameters": {**details, **overrides},
                "dependencies": ["asset_exists"],
            },
            {
                "step_number": 3,
                "action": "update_asset",
                "description": "更新资产",
                "parameters": {
                    **details,
                    **overrides,
                },
                "dependencies": ["asset_exists", "parameters_valid"],
                "stop_on_error": True,
            },
        ]

    def _generate_node_registration_steps(
        self, audit_log: AuditLog, overrides: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成节点注册的回放步骤"""
        details = audit_log.details or {}

        return [
            {
                "step_number": 1,
                "action": "validate_node_info",
                "description": "验证节点信息",
                "parameters": {**details, **overrides},
                "dependencies": [],
            },
            {
                "step_number": 2,
                "action": "register_node",
                "description": "注册节点",
                "parameters": {
                    **details,
                    **overrides,
                },
                "dependencies": ["node_info_valid"],
                "stop_on_error": True,
            },
        ]

    def _extract_dependencies(self, audit_log: AuditLog) -> List[str]:
        """提取依赖项"""
        dependencies = []

        # 基于目标类型的依赖
        if audit_log.target_type == "task":
            dependencies.append("device_exists")
            dependencies.append("node_exists")
        elif audit_log.target_type == "asset":
            dependencies.append("asset_parameters_valid")
        elif audit_log.target_type == "node":
            dependencies.append("node_info_valid")

        return dependencies

    def _check_dependency(self, dependency: str) -> bool:
        """检查依赖项是否可用"""
        # 这里可以添加实际的依赖项检查逻辑
        # 目前简化为总是返回True
        return True

    def _estimate_duration(self, steps: List[Dict[str, Any]]) -> int:
        """估算回放持续时间（秒）"""
        # 简单估算：每个步骤5秒
        return len(steps) * 5

    def _execute_step(self, step: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个回放步骤"""
        # 这里应该实现实际的步骤执行逻辑
        # 目前简化为返回模拟结果

        action = step.get("action")
        parameters = step.get("parameters", {})

        # 模拟执行
        return {
            "action": action,
            "parameters": parameters,
            "result": f"步骤 '{action}' 执行成功",
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _log_replay_action(
        self,
        replay_id: str,
        original_audit: AuditLog,
        mode: ReplayMode,
        actor: str,
        result: Dict[str, Any],
    ):
        """记录回放操作"""
        if not self.audit_service:
            return

        from shared.models.audit import AuditLogCreateRequest, AuditAction

        # 处理mode参数（可能是字符串或枚举）
        mode_value = mode.value if isinstance(mode, ReplayMode) else str(mode)
        result_status = result.get("status", "unknown")

        # 创建回放操作的审计日志
        replay_log = AuditLogCreateRequest(
            action=AuditAction.AUDIT_REPLAYED,  # 审计回放action
            category=AuditCategory.AUDIT,
            level="info",
            actor=actor,
            actor_type="user",
            target_type="audit_log",
            target_id=original_audit.audit_id,
            related_task_id=original_audit.related_task_id,
            related_node_id=original_audit.related_node_id,
            related_asset_id=original_audit.related_asset_id,
            details={
                "replay_id": replay_id,
                "original_action": original_audit.action.value,
                "replay_mode": mode_value,
                "replay_result": result_status,
            },
            message=f"审计回放: {original_audit.action.value} ({mode_value})",
        )

        try:
            self.audit_service.log_action(replay_log)
        except Exception as e:
            # 记录失败不应影响回放操作
            print(f"Warning: Failed to log replay action: {e}")


# 全局服务实例
_replay_service_instance = None


def get_replay_service(audit_service=None) -> AuditReplayService:
    """获取审计回放服务实例"""
    global _replay_service_instance
    if _replay_service_instance is None:
        _replay_service_instance = AuditReplayService(audit_service)
    return _replay_service_instance
