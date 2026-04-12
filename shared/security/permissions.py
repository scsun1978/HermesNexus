"""
HermesNexus Phase 2 - Permission Checker
权限检查器 - 定义和检查操作权限
"""

from enum import Enum
from typing import List, Set


class Permission(str, Enum):
    """权限枚举"""
    # 资源管理权限
    ASSET_READ = "asset:read"
    ASSET_WRITE = "asset:write"
    ASSET_DELETE = "asset:delete"

    # 任务管理权限
    TASK_READ = "task:read"
    TASK_WRITE = "task:write"
    TASK_DELETE = "task:delete"
    TASK_EXECUTE = "task:execute"

    # 审计日志权限
    AUDIT_READ = "audit:read"

    # 节点管理权限
    NODE_READ = "node:read"
    NODE_WRITE = "node:write"

    # 用户管理权限
    USER_READ = "user:read"
    USER_WRITE = "user:write"

    # 系统管理权限
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_STATS = "system:stats"


class PermissionChecker:
    """权限检查器"""

    # 角色默认权限映射
    ROLE_PERMISSIONS = {
        "admin": [
            Permission.SYSTEM_ADMIN,
            Permission.ASSET_READ,
            Permission.ASSET_WRITE,
            Permission.ASSET_DELETE,
            Permission.TASK_READ,
            Permission.TASK_WRITE,
            Permission.TASK_DELETE,
            Permission.TASK_EXECUTE,
            Permission.AUDIT_READ,
            Permission.NODE_READ,
            Permission.NODE_WRITE,
            Permission.SYSTEM_STATS,
        ],
        "operator": [
            Permission.ASSET_READ,
            Permission.TASK_READ,
            Permission.TASK_WRITE,
            Permission.TASK_EXECUTE,
            Permission.AUDIT_READ,
            Permission.NODE_READ,
            Permission.SYSTEM_STATS,
        ],
        "viewer": [
            Permission.ASSET_READ,
            Permission.TASK_READ,
            Permission.AUDIT_READ,
            Permission.NODE_READ,
            Permission.SYSTEM_STATS,
        ],
        "user": [
            Permission.ASSET_READ,
            Permission.TASK_READ,
        ],
    }

    @classmethod
    def get_role_permissions(cls, role: str) -> List[Permission]:
        """
        获取角色的默认权限

        Args:
            role: 角色名称

        Returns:
            权限列表
        """
        return cls.ROLE_PERMISSIONS.get(role, [])

    @classmethod
    def check_permission(cls, user_permissions: List[str], required_permission: Permission) -> bool:
        """
        检查用户是否有指定权限

        Args:
            user_permissions: 用户权限列表
            required_permission: 需要的权限

        Returns:
            是否有权限
        """
        # 检查通配符权限
        if "*" in user_permissions:
            return True

        # 检查系统管理员权限
        if Permission.SYSTEM_ADMIN.value in user_permissions:
            return True

        # 检查具体权限
        return required_permission.value in user_permissions

    @classmethod
    def check_any_permission(cls, user_permissions: List[str], required_permissions: List[Permission]) -> bool:
        """
        检查用户是否有任意一个指定权限

        Args:
            user_permissions: 用户权限列表
            required_permissions: 需要的权限列表

        Returns:
            是否有任意一个权限
        """
        for permission in required_permissions:
            if cls.check_permission(user_permissions, permission):
                return True
        return False

    @classmethod
    def check_all_permissions(cls, user_permissions: List[str], required_permissions: List[Permission]) -> bool:
        """
        检查用户是否有所有指定权限

        Args:
            user_permissions: 用户权限列表
            required_permissions: 需要的权限列表

        Returns:
            是否有所有权限
        """
        for permission in required_permissions:
            if not cls.check_permission(user_permissions, permission):
                return False
        return True


# 操作权限映射
OPERATION_PERMISSIONS = {
    # 资产操作
    "GET:/api/v1/assets": [Permission.ASSET_READ],
    "POST:/api/v1/assets": [Permission.ASSET_WRITE],
    "PUT:/api/v1/assets/{id}": [Permission.ASSET_WRITE],
    "DELETE:/api/v1/assets/{id}": [Permission.ASSET_DELETE],

    # 任务操作
    "GET:/api/v1/tasks": [Permission.TASK_READ],
    "POST:/api/v1/tasks": [Permission.TASK_WRITE],
    "PUT:/api/v1/tasks/{id}": [Permission.TASK_WRITE],
    "DELETE:/api/v1/tasks/{id}": [Permission.TASK_DELETE],
    "POST:/api/v1/tasks/{id}/cancel": [Permission.TASK_EXECUTE],
    "POST:/api/v1/tasks/dispatch": [Permission.TASK_EXECUTE],
    "POST:/api/v1/tasks/{id}/result": [Permission.TASK_EXECUTE],

    # 审计日志操作
    "GET:/api/v1/audit_logs": [Permission.AUDIT_READ],
    "GET:/api/v1/audit_logs/{id}": [Permission.AUDIT_READ],

    # 节点操作
    "GET:/api/v1/nodes": [Permission.NODE_READ],
    "POST:/api/v1/nodes/{id}/heartbeat": [Permission.NODE_WRITE],

    # 系统操作
    "GET:/api/v1/stats": [Permission.SYSTEM_STATS],
    "GET:/health": [],  # 健康检查不需要权限
}


def get_required_permissions(method: str, path: str) -> List[Permission]:
    """
    获取操作所需的权限

    Args:
        method: HTTP方法
        path: 请求路径

    Returns:
        所需权限列表
    """
    # 规范化路径
    normalized_path = path
    for placeholder in ["{id}", "{task_id}", "{asset_id}", "{node_id}", "{audit_id}"]:
        normalized_path = normalized_path.replace(placeholder, "{id}")

    key = f"{method}:{normalized_path}"
    return OPERATION_PERMISSIONS.get(key, [])
