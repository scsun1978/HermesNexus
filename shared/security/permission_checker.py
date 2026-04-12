"""
HermesNexus Phase 3 - 权限检查器
实现权限检查的核心逻辑，结合身份、权限矩阵和风险评估
"""

from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import fnmatch
import re

from shared.models.permission import (
    Permission, PermissionContext, PermissionCheckResult,
    PermissionMatrix, ActionType, ResourceType, RiskLevel,
    BuiltInRoles
)
from shared.security.risk_assessor import RiskAssessor, get_risk_assessor


class PermissionChecker:
    """权限检查器 - 核心权限判断逻辑"""

    def __init__(
        self,
        permission_matrix: Optional[PermissionMatrix] = None,
        risk_assessor: Optional[RiskAssessor] = None
    ):
        """
        初始化权限检查器

        Args:
            permission_matrix: 权限矩阵
            risk_assessor: 风险评估器
        """
        self.permission_matrix = permission_matrix or self._create_default_matrix()
        self.risk_assessor = risk_assessor or get_risk_assessor()

        # 编译正则表达式缓存
        self._compiled_patterns: Dict[str, re.Pattern] = {}

    def check_permission(
        self,
        action: ActionType,
        resource: ResourceType,
        context: PermissionContext,
        resource_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> PermissionCheckResult:
        """
        检查权限

        Args:
            action: 操作动作
            resource: 资源类型
            context: 权限上下文
            resource_id: 资源ID（用于特定资源权限检查）
            additional_context: 额外的上下文信息

        Returns:
            权限检查结果
        """
        # 1. 首先检查黑名单
        if self._is_blacklisted(action, resource):
            return PermissionCheckResult(
                allowed=False,
                reason="操作在黑名单中，禁止执行",
                risk_level=RiskLevel.HIGH,
                requires_approval=False
            )

        # 2. 检查白名单
        if self._is_whitelisted(action, resource):
            return PermissionCheckResult(
                allowed=True,
                reason="操作在白名单中，允许执行",
                risk_level=RiskLevel.LOW,
                requires_approval=False
            )

        # 3. 评估操作风险
        risk_context = additional_context or {}
        risk_level = self.risk_assessor.assess_risk(action, resource, risk_context)

        # 4. 检查时间有效性
        if not self._is_time_valid(context):
            return PermissionCheckResult(
                allowed=False,
                reason="权限不在有效期内",
                risk_level=risk_level,
                requires_approval=False
            )

        # 5. 检查租户和区域权限
        if not self._check_tenant_region_permission(context, resource_id, additional_context):
            return PermissionCheckResult(
                allowed=False,
                reason="用户无权访问该租户或区域的资源",
                risk_level=risk_level,
                requires_approval=False
            )

        # 6. 检查角色权限
        permission_result = self._check_role_permission(action, resource, context)
        if not permission_result["has_permission"]:
            return PermissionCheckResult(
                allowed=False,
                reason=f"权限不足: {', '.join(permission_result['missing_permissions'])}",
                risk_level=risk_level,
                requires_approval=self.risk_assessor.requires_approval(risk_level),
                missing_permissions=permission_result["missing_permissions"]
            )

        # 7. 检查资源类型限制
        if resource == ResourceType.ASSET and additional_context:
            asset_type = additional_context.get("asset_type")
            if asset_type and not self._is_asset_type_allowed(context, asset_type):
                return PermissionCheckResult(
                    allowed=False,
                    reason=f"用户无权操作 {asset_type} 类型的设备",
                    risk_level=risk_level,
                    requires_approval=False
                )

        # 8. 权限检查通过
        return PermissionCheckResult(
            allowed=True,
            reason="",
            risk_level=risk_level,
            requires_approval=self.risk_assessor.requires_approval(risk_level)
        )

    def batch_check_permissions(
        self,
        operations: List[Dict[str, Any]],
        context: PermissionContext
    ) -> List[PermissionCheckResult]:
        """
        批量检查权限

        Args:
            operations: 操作列表
            context: 权限上下文

        Returns:
            权限检查结果列表
        """
        results = []
        for op in operations:
            action = op.get("action")
            resource = op.get("resource")
            resource_id = op.get("resource_id")
            additional_context = op.get("context", {})

            result = self.check_permission(
                action, resource, context, resource_id, additional_context
            )
            results.append(result)

        return results

    def get_user_permissions(
        self,
        context: PermissionContext
    ) -> List[Permission]:
        """
        获取用户的所有权限

        Args:
            context: 权限上下文

        Returns:
            权限列表
        """
        permissions = []

        # 遍历用户的所有角色
        for role in context.roles:
            role_perms = self.permission_matrix.role_permissions.get(role, [])
            permissions.extend(role_perms)

        return permissions

    def has_role(self, context: PermissionContext, role: str) -> bool:
        """
        检查用户是否具有特定角色

        Args:
            context: 权限上下文
            role: 角色名称

        Returns:
            是否具有该角色
        """
        return role in context.roles

    def is_super_admin(self, context: PermissionContext) -> bool:
        """检查是否为超级管理员"""
        return self.has_role(context, BuiltInRoles.SUPER_ADMIN)

    def _is_blacklisted(self, action: ActionType, resource: ResourceType) -> bool:
        """检查操作是否在黑名单中"""
        action_resource = f"{action.value}.{resource.value}"

        for blacklist_pattern in self.permission_matrix.blacklist:
            if self._matches_pattern(action_resource, blacklist_pattern):
                return True

        return False

    def _is_whitelisted(self, action: ActionType, resource: ResourceType) -> bool:
        """检查操作是否在白名单中"""
        action_resource = f"{action.value}.{resource.value}"

        for whitelist_pattern in self.permission_matrix.whitelist:
            if self._matches_pattern(action_resource, whitelist_pattern):
                return True

        return False

    def _check_role_permission(
        self,
        action: ActionType,
        resource: ResourceType,
        context: PermissionContext
    ) -> Dict[str, Any]:
        """
        检查角色权限

        Returns:
            包含 has_permission 和 missing_permissions 的字典
        """
        # 超级管理员拥有所有权限
        if self.is_super_admin(context):
            return {"has_permission": True, "missing_permissions": []}

        missing_permissions = []
        has_permission = False

        # 检查用户的所有角色
        for role in context.roles:
            role_permissions = self.permission_matrix.role_permissions.get(role, [])

            for perm in role_permissions:
                # 检查是否匹配权限
                if self._permission_matches(perm, action, resource, context):
                    has_permission = True
                    break

            if has_permission:
                break

        # 如果没有权限，记录缺失的权限
        if not has_permission:
            required_permission = f"{action.value}.{resource.value}"
            missing_permissions.append(required_permission)

        return {
            "has_permission": has_permission,
            "missing_permissions": missing_permissions
        }

    def _permission_matches(
        self,
        permission: Permission,
        action: ActionType,
        resource: ResourceType,
        context: PermissionContext
    ) -> bool:
        """检查权限是否匹配"""
        # 检查动作匹配（支持通配符）
        if permission.action != ActionType.ALL and permission.action != action:
            return False

        # 检查资源匹配（支持通配符）
        if permission.resource != ResourceType.ALL and permission.resource != resource:
            return False

        # 检查条件匹配
        if permission.conditions:
            for key, value in permission.conditions.items():
                context_value = getattr(context, key, None)
                if context_value != value:
                    return False

        return True

    def _is_time_valid(self, context: PermissionContext) -> bool:
        """检查时间有效性"""
        now = int(datetime.now().timestamp())

        # 检查生效时间
        if context.not_before and now < context.not_before:
            return False

        # 检查失效时间
        if context.not_after and now > context.not_after:
            return False

        return True

    def _check_tenant_region_permission(
        self,
        context: PermissionContext,
        resource_id: Optional[str],
        additional_context: Optional[Dict[str, Any]]
    ) -> bool:
        """检查租户和区域权限"""
        # 如果没有租户限制，则通过
        if not context.tenant_id:
            return True

        # 检查资源的租户匹配
        if additional_context and "tenant_id" in additional_context:
            if additional_context["tenant_id"] != context.tenant_id:
                return False

        # 检查区域权限
        if additional_context and "region_id" in additional_context:
            resource_region = additional_context["region_id"]
            if resource_region not in context.allowed_regions:
                return False

        return True

    def _is_asset_type_allowed(self, context: PermissionContext, asset_type: str) -> bool:
        """检查是否允许操作特定类型的设备"""
        if not context.allowed_asset_types:
            return True  # 没有限制，允许所有类型

        return asset_type in context.allowed_asset_types

    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """检查文本是否匹配模式（支持通配符）"""
        # 如果模式包含通配符，使用fnmatch
        if "*" in pattern or "?" in pattern:
            return fnmatch.fnmatch(text, pattern)

        # 否则直接比较
        return text == pattern

    def _create_default_matrix(self) -> PermissionMatrix:
        """创建默认权限矩阵"""
        from shared.models.permission import CommonPermissions

        return PermissionMatrix(
            matrix_id="default-matrix",
            name="默认权限矩阵",
            description="系统默认的权限控制矩阵",
            role_permissions={
                BuiltInRoles.SUPER_ADMIN: [
                    Permission(action=ActionType.ALL, resource=ResourceType.ALL, risk_level=RiskLevel.LOW)
                ],
                BuiltInRoles.TENANT_ADMIN: [
                    Permission(action=ActionType.READ, resource=ResourceType.ASSET, risk_level=RiskLevel.LOW),
                    Permission(action=ActionType.CREATE, resource=ResourceType.ASSET, risk_level=RiskLevel.MEDIUM),
                    Permission(action=ActionType.UPDATE, resource=ResourceType.ASSET, risk_level=RiskLevel.MEDIUM),
                    Permission(action=ActionType.DELETE, resource=ResourceType.ASSET, risk_level=RiskLevel.HIGH),
                    Permission(action=ActionType.EXECUTE, resource=ResourceType.TASK, risk_level=RiskLevel.MEDIUM),
                    Permission(action=ActionType.READ, resource=ResourceType.NODE, risk_level=RiskLevel.LOW),
                ],
                BuiltInRoles.OPERATOR: CommonPermissions.OPERATOR,
                BuiltInRoles.VIEWER: CommonPermissions.READ_ONLY,
            },
            default_policy="deny",
            whitelist=["health.check", "system.ping"],
            blacklist=["system.shutdown", "data.delete_all", "*.drop.*"],
            high_risk_actions=[
                "delete", "deregister", "restart", "rollback",
                "grant", "revoke", "admin"
            ],
            created_at=int(datetime.now().timestamp()),
            updated_at=int(datetime.now().timestamp())
        )


# 全局权限检查器实例（延迟初始化）
_global_permission_checker: Optional[PermissionChecker] = None


def get_permission_checker() -> PermissionChecker:
    """获取全局权限检查器实例"""
    global _global_permission_checker
    if _global_permission_checker is None:
        _global_permission_checker = PermissionChecker()
    return _global_permission_checker


def create_permission_checker(
    permission_matrix: PermissionMatrix,
    risk_assessor: Optional[RiskAssessor] = None
) -> PermissionChecker:
    """
    创建自定义权限检查器

    Args:
        permission_matrix: 自定义权限矩阵
        risk_assessor: 自定义风险评估器

    Returns:
        权限检查器实例
    """
    return PermissionChecker(
        permission_matrix=permission_matrix,
        risk_assessor=risk_assessor
    )


# 权限检查装饰器
def require_permission(
    action: ActionType,
    resource: ResourceType,
    check_tenant_region: bool = True
):
    """
    权限检查装饰器

    Args:
        action: 需要的操作权限
        resource: 需要的资源权限
        check_tenant_region: 是否检查租户区域权限

    Usage:
        @require_permission(ActionType.READ, ResourceType.ASSET)
        def get_asset(asset_id: str):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 这里需要从请求上下文中获取权限信息
            # 实际实现中会从HTTP请求头或Token中提取
            # 这里只是示例框架
            permission_checker = get_permission_checker()

            # 构建权限上下文（实际应该从请求中获取）
            context = PermissionContext(
                user_id="current_user",  # 从请求中获取
                roles=["operator"],  # 从用户信息中获取
                tenant_id="tenant-001",  # 从用户信息中获取
            )

            # 执行权限检查
            result = permission_checker.check_permission(action, resource, context)

            if not result.allowed:
                raise PermissionError(f"权限不足: {result.reason}")

            if result.requires_approval:
                raise PermissionError(f"操作需要审批: 风险等级 {result.risk_level}")

            # 权限检查通过，执行原函数
            return func(*args, **kwargs)

        return wrapper
    return decorator