"""
HermesNexus Phase 3 - 风险评估器
根据操作类型、资源类型和上下文信息自动评估操作风险等级
"""

from typing import Dict, Any, Optional, List
import re

from shared.models.permission import ActionType, ResourceType, RiskLevel


class RiskAssessor:
    """风险评估器 - 评估操作的风险等级"""

    # 默认风险等级映射
    DEFAULT_RISK_MAPPING = {
        # 查询操作 - 低风险
        ActionType.READ: RiskLevel.LOW,
        ActionType.LIST: RiskLevel.LOW,
        ActionType.GET: RiskLevel.LOW,
        ActionType.QUERY: RiskLevel.LOW,
        ActionType.DESCRIBE: RiskLevel.LOW,
        # 修改操作 - 中风险
        ActionType.CREATE: RiskLevel.MEDIUM,
        ActionType.UPDATE: RiskLevel.MEDIUM,
        ActionType.MODIFY: RiskLevel.MEDIUM,
        ActionType.CHANGE: RiskLevel.MEDIUM,
        ActionType.CONFIGURE: RiskLevel.MEDIUM,
        # 删除操作 - 高风险
        ActionType.DELETE: RiskLevel.HIGH,
        ActionType.REMOVE: RiskLevel.HIGH,
        ActionType.UNBIND: RiskLevel.HIGH,
        ActionType.DEREGISTER: RiskLevel.HIGH,
        # 执行操作 - 中高风险
        ActionType.EXECUTE: RiskLevel.MEDIUM,
        ActionType.START: RiskLevel.MEDIUM,
        ActionType.STOP: RiskLevel.MEDIUM,
        ActionType.RESTART: RiskLevel.HIGH,
        ActionType.DEPLOY: RiskLevel.HIGH,
        ActionType.ROLLBACK: RiskLevel.HIGH,
        # 管理操作 - 高风险
        ActionType.APPROVE: RiskLevel.HIGH,
        ActionType.REJECT: RiskLevel.HIGH,
        ActionType.GRANT: RiskLevel.HIGH,
        ActionType.REVOKE: RiskLevel.HIGH,
        ActionType.ADMIN: RiskLevel.HIGH,
        # 节点操作 - 低风险
        ActionType.HEARTBEAT: RiskLevel.LOW,
        ActionType.STATUS: RiskLevel.LOW,
        ActionType.REPORT: RiskLevel.LOW,
    }

    # 资源类型风险调整因子
    RESOURCE_RISK_FACTORS = {
        ResourceType.CONFIG: 1,  # 配置操作风险因子为1（保持原风险等级）
        ResourceType.ASSET: 1,  # 资产操作风险因子为1
        ResourceType.TASK: 1,  # 任务操作风险因子为1（保持原风险等级）
        ResourceType.NODE: 1.2,  # 节点操作风险因子为1.2（略微提高）
        ResourceType.USER: 1.5,  # 用户操作风险因子为1.5（显著提高）
        ResourceType.TENANT: 2.0,  # 租户操作风险因子为2.0（大幅提高）
        ResourceType.REGION: 1.5,  # 区域操作风险因子为1.5（显著提高）
        ResourceType.LOG: 0.5,  # 日志操作风险因子为0.5（降低）
        ResourceType.AUDIT: 0.3,  # 审计操作风险因子为0.3（大幅降低）
    }

    # 特定操作的高风险模式
    HIGH_RISK_PATTERNS = [
        r"delete.*all",  # 删除所有
        r"shutdown",  # 关闭系统
        r"reboot.*all",  # 重启所有
        r"wipe",  # 擦除数据
        r"format",  # 格式化
        r"drop.*table",  # 删除表
        r"truncate",  # 清空表
        r"grant.*admin",  # 授予管理员权限
        r"disable.*security",  # 禁用安全
        r"bypass.*auth",  # 绕过认证
    ]

    # 需要额外确认的操作
    CONFIRMATION_REQUIRED_ACTIONS = {
        ActionType.DELETE,
        ActionType.DEREGISTER,
        ActionType.RESTART,
        ActionType.DEPLOY,
        ActionType.ROLLBACK,
        ActionType.GRANT,
        ActionType.REVOKE,
    }

    def __init__(self, custom_mapping: Optional[Dict[ActionType, RiskLevel]] = None):
        """
        初始化风险评估器

        Args:
            custom_mapping: 自定义的风险等级映射
        """
        self.risk_mapping = custom_mapping or self.DEFAULT_RISK_MAPPING.copy()

    def assess_risk(
        self,
        action: ActionType,
        resource: ResourceType,
        context: Optional[Dict[str, Any]] = None,
        custom_rules: Optional[List[Dict[str, Any]]] = None,
    ) -> RiskLevel:
        """
        评估操作的风险等级

        Args:
            action: 操作动作
            resource: 资源类型
            context: 操作上下文信息
            custom_rules: 自定义规则列表

        Returns:
            风险等级
        """
        # 1. 获取基础风险等级
        base_risk = self._get_base_risk(action)

        # 2. 应用资源类型调整
        adjusted_risk = self._apply_resource_factor(base_risk, resource)

        # 3. 检查高风险模式
        if self._matches_high_risk_pattern(context):
            adjusted_risk = RiskLevel.HIGH

        # 4. 应用自定义规则
        if custom_rules:
            adjusted_risk = self._apply_custom_rules(
                adjusted_risk, action, resource, context, custom_rules
            )

        return adjusted_risk

    def requires_approval(self, risk_level: RiskLevel) -> bool:
        """
        判断是否需要审批

        Args:
            risk_level: 风险等级

        Returns:
            是否需要审批
        """
        return risk_level == RiskLevel.HIGH

    def requires_confirmation(self, action: ActionType) -> bool:
        """
        判断是否需要额外确认

        Args:
            action: 操作动作

        Returns:
            是否需要确认
        """
        return action in self.CONFIRMATION_REQUIRED_ACTIONS

    def batch_assess_risk(
        self, operations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量评估操作风险

        Args:
            operations: 操作列表，每个操作包含 action, resource, context

        Returns:
            评估结果列表
        """
        results = []
        for op in operations:
            action = op.get("action")
            resource = op.get("resource")
            context = op.get("context", {})

            risk_level = self.assess_risk(action, resource, context)
            needs_approval = self.requires_approval(risk_level)
            needs_confirmation = self.requires_confirmation(action)

            results.append(
                {
                    "action": action,
                    "resource": resource,
                    "risk_level": risk_level,
                    "requires_approval": needs_approval,
                    "requires_confirmation": needs_confirmation,
                }
            )

        return results

    def _get_base_risk(self, action: ActionType) -> RiskLevel:
        """获取操作的基础风险等级"""
        return self.risk_mapping.get(action, RiskLevel.MEDIUM)

    def _apply_resource_factor(
        self, base_risk: RiskLevel, resource: ResourceType
    ) -> RiskLevel:
        """应用资源类型风险调整因子"""
        factor = self.RESOURCE_RISK_FACTORS.get(resource, 1.0)

        # 风险等级数值映射
        risk_values = {RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3}
        base_value = risk_values[base_risk]

        # 应用调整因子
        adjusted_value = int(base_value * factor)

        # 限制在合理范围内
        adjusted_value = max(1, min(3, adjusted_value))

        # 转换回风险等级
        value_to_risk = {1: RiskLevel.LOW, 2: RiskLevel.MEDIUM, 3: RiskLevel.HIGH}
        return value_to_risk[adjusted_value]

    def _matches_high_risk_pattern(self, context: Optional[Dict[str, Any]]) -> bool:
        """检查是否匹配高风险模式"""
        if not context:
            return False

        # 检查操作描述、命令等文本内容
        text_content = ""
        if "description" in context:
            text_content += context["description"].lower()
        if "command" in context:
            text_content += " " + context["command"].lower()
        if "script_content" in context:
            text_content += " " + context["script_content"].lower()

        if not text_content:
            return False

        # 检查是否匹配任何高风险模式
        for pattern in self.HIGH_RISK_PATTERNS:
            if re.search(pattern, text_content):
                return True

        return False

    def _apply_custom_rules(
        self,
        current_risk: RiskLevel,
        action: ActionType,
        resource: ResourceType,
        context: Optional[Dict[str, Any]],
        custom_rules: List[Dict[str, Any]],
    ) -> RiskLevel:
        """应用自定义规则调整风险等级"""
        for rule in custom_rules:
            # 检查规则是否匹配
            if self._rule_matches(rule, action, resource, context):
                # 应用规则的风险等级
                override_risk = rule.get("override_risk")
                if override_risk:
                    return RiskLevel(override_risk)

                # 应用风险调整
                risk_adjustment = rule.get("risk_adjustment", 0)
                if risk_adjustment != 0:
                    risk_values = {
                        RiskLevel.LOW: 1,
                        RiskLevel.MEDIUM: 2,
                        RiskLevel.HIGH: 3,
                    }
                    current_value = risk_values[current_risk]
                    adjusted_value = max(1, min(3, current_value + risk_adjustment))
                    value_to_risk = {
                        1: RiskLevel.LOW,
                        2: RiskLevel.MEDIUM,
                        3: RiskLevel.HIGH,
                    }
                    return value_to_risk[adjusted_value]

        return current_risk

    def _rule_matches(
        self,
        rule: Dict[str, Any],
        action: ActionType,
        resource: ResourceType,
        context: Optional[Dict[str, Any]],
    ) -> bool:
        """检查自定义规则是否匹配当前操作"""
        # 检查动作匹配
        if "action" in rule and rule["action"] != action:
            return False

        # 检查资源匹配
        if "resource" in rule and rule["resource"] != resource:
            return False

        # 检查上下文条件
        if "conditions" in rule and context:
            for key, value in rule["conditions"].items():
                if context.get(key) != value:
                    return False

        return True


# 全局风险评估器实例（延迟初始化）
_global_risk_assessor: Optional[RiskAssessor] = None


def get_risk_assessor() -> RiskAssessor:
    """获取全局风险评估器实例"""
    global _global_risk_assessor
    if _global_risk_assessor is None:
        _global_risk_assessor = RiskAssessor()
    return _global_risk_assessor


def create_custom_risk_assessor(
    low_risk_actions: List[ActionType], high_risk_actions: List[ActionType]
) -> RiskAssessor:
    """
    创建自定义风险评估器

    Args:
        low_risk_actions: 指定为低风险的操作列表
        high_risk_actions: 指定为高风险的操作列表

    Returns:
        自定义风险评估器实例
    """
    custom_mapping = RiskAssessor.DEFAULT_RISK_MAPPING.copy()

    # 应用低风险自定义
    for action in low_risk_actions:
        custom_mapping[action] = RiskLevel.LOW

    # 应用高风险自定义
    for action in high_risk_actions:
        custom_mapping[action] = RiskLevel.HIGH

    return RiskAssessor(custom_mapping=custom_mapping)
