"""
HermesNexus Phase 3 - 权限矩阵管理
权限矩阵的加载、存储和管理功能
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from shared.models.permission import (
    PermissionMatrix, Permission, ActionType,
    ResourceType, RiskLevel, BuiltInRoles
)


class PermissionMatrixManager:
    """权限矩阵管理器"""

    def __init__(self, config_dir: str = "config"):
        """
        初始化权限矩阵管理器

        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 权限矩阵缓存
        self._matrix_cache: Dict[str, PermissionMatrix] = {}

    def load_matrix(self, matrix_id: str, force_reload: bool = False) -> Optional[PermissionMatrix]:
        """
        加载权限矩阵

        Args:
            matrix_id: 权限矩阵ID
            force_reload: 是否强制重新加载

        Returns:
            权限矩阵对象，如果不存在则返回None
        """
        # 检查缓存
        if not force_reload and matrix_id in self._matrix_cache:
            return self._matrix_cache[matrix_id]

        # 构建文件路径
        matrix_file = self.config_dir / f"{matrix_id}.json"

        if not matrix_file.exists():
            return None

        try:
            # 读取JSON文件
            with open(matrix_file, 'r', encoding='utf-8') as f:
                matrix_data = json.load(f)

            # 转换为PermissionMatrix对象
            matrix = self._dict_to_matrix(matrix_data)

            # 缓存矩阵
            self._matrix_cache[matrix_id] = matrix

            return matrix

        except Exception as e:
            print(f"加载权限矩阵失败: {e}")
            return None

    def save_matrix(self, matrix: PermissionMatrix) -> bool:
        """
        保存权限矩阵

        Args:
            matrix: 权限矩阵对象

        Returns:
            是否保存成功
        """
        try:
            # 更新时间戳
            matrix.updated_at = int(datetime.now().timestamp())

            # 转换为字典
            matrix_data = self._matrix_to_dict(matrix)

            # 构建文件路径
            matrix_file = self.config_dir / f"{matrix.matrix_id}.json"

            # 保存JSON文件
            with open(matrix_file, 'w', encoding='utf-8') as f:
                json.dump(matrix_data, f, indent=2, ensure_ascii=False)

            # 更新缓存
            self._matrix_cache[matrix.matrix_id] = matrix

            return True

        except Exception as e:
            print(f"保存权限矩阵失败: {e}")
            return False

    def list_matrices(self) -> List[str]:
        """
        列出所有权限矩阵

        Returns:
            权限矩阵ID列表
        """
        matrix_files = list(self.config_dir.glob("*.json"))
        return [f.stem for f in matrix_files if f.stem != "permissions"]

    def delete_matrix(self, matrix_id: str) -> bool:
        """
        删除权限矩阵

        Args:
            matrix_id: 权限矩阵ID

        Returns:
            是否删除成功
        """
        try:
            # 删除文件
            matrix_file = self.config_dir / f"{matrix_id}.json"
            if matrix_file.exists():
                matrix_file.unlink()

            # 清除缓存
            if matrix_id in self._matrix_cache:
                del self._matrix_cache[matrix_id]

            return True

        except Exception as e:
            print(f"删除权限矩阵失败: {e}")
            return False

    def create_matrix(
        self,
        matrix_id: str,
        name: str,
        description: Optional[str] = None,
        base_matrix: Optional[str] = None
    ) -> Optional[PermissionMatrix]:
        """
        创建新的权限矩阵

        Args:
            matrix_id: 权限矩阵ID
            name: 权限矩阵名称
            description: 权限矩阵描述
            base_matrix: 基于现有矩阵创建（可选）

        Returns:
            新创建的权限矩阵对象
        """
        try:
            # 如果指定了基础矩阵，则基于它创建
            if base_matrix:
                base = self.load_matrix(base_matrix)
                if not base:
                    raise ValueError(f"基础矩阵不存在: {base_matrix}")

                matrix = PermissionMatrix(
                    matrix_id=matrix_id,
                    name=name,
                    description=description,
                    role_permissions=base.role_permissions.copy(),
                    default_policy=base.default_policy,
                    whitelist=base.whitelist.copy(),
                    blacklist=base.blacklist.copy(),
                    high_risk_actions=base.high_risk_actions.copy(),
                    created_at=int(datetime.now().timestamp()),
                    updated_at=int(datetime.now().timestamp())
                )
            else:
                # 创建空矩阵
                matrix = PermissionMatrix(
                    matrix_id=matrix_id,
                    name=name,
                    description=description,
                    created_at=int(datetime.now().timestamp()),
                    updated_at=int(datetime.now().timestamp())
                )

            # 保存矩阵
            if self.save_matrix(matrix):
                return matrix

            return None

        except Exception as e:
            print(f"创建权限矩阵失败: {e}")
            return None

    def add_role_permission(
        self,
        matrix_id: str,
        role: str,
        permission: Permission
    ) -> bool:
        """
        为角色添加权限

        Args:
            matrix_id: 权限矩阵ID
            role: 角色名称
            permission: 权限对象

        Returns:
            是否添加成功
        """
        try:
            matrix = self.load_matrix(matrix_id, force_reload=True)
            if not matrix:
                return False

            # 添加权限
            if role not in matrix.role_permissions:
                matrix.role_permissions[role] = []

            matrix.role_permissions[role].append(permission)

            # 保存更新
            return self.save_matrix(matrix)

        except Exception as e:
            print(f"添加角色权限失败: {e}")
            return False

    def remove_role_permission(
        self,
        matrix_id: str,
        role: str,
        action: ActionType,
        resource: ResourceType
    ) -> bool:
        """
        移除角色权限

        Args:
            matrix_id: 权限矩阵ID
            role: 角色名称
            action: 操作动作
            resource: 资源类型

        Returns:
            是否移除成功
        """
        try:
            matrix = self.load_matrix(matrix_id, force_reload=True)
            if not matrix:
                return False

            # 移除权限
            if role in matrix.role_permissions:
                matrix.role_permissions[role] = [
                    perm for perm in matrix.role_permissions[role]
                    if not (perm.action == action and perm.resource == resource)
                ]

            # 保存更新
            return self.save_matrix(matrix)

        except Exception as e:
            print(f"移除角色权限失败: {e}")
            return False

    def get_role_permissions(
        self,
        matrix_id: str,
        role: str
    ) -> List[Permission]:
        """
        获取角色的所有权限

        Args:
            matrix_id: 权限矩阵ID
            role: 角色名称

        Returns:
            权限列表
        """
        matrix = self.load_matrix(matrix_id)
        if not matrix:
            return []

        return matrix.role_permissions.get(role, [])

    def _dict_to_matrix(self, data: Dict[str, Any]) -> PermissionMatrix:
        """将字典转换为PermissionMatrix对象"""
        # 转换角色权限
        role_permissions = {}
        for role, perms in data.get("role_permissions", {}).items():
            role_permissions[role] = [
                Permission(
                    action=ActionType(perm["action"]),
                    resource=ResourceType(perm["resource"]),
                    conditions=perm.get("conditions", {}),
                    risk_level=RiskLevel(perm.get("risk_level", "low")),
                    description=perm.get("description")
                )
                for perm in perms
            ]

        return PermissionMatrix(
            matrix_id=data["matrix_id"],
            name=data["name"],
            description=data.get("description"),
            role_permissions=role_permissions,
            default_policy=data.get("default_policy", "deny"),
            whitelist=data.get("whitelist", []),
            blacklist=data.get("blacklist", []),
            high_risk_actions=data.get("high_risk_actions", []),
            version=data.get("version", "1.0.0"),
            created_at=data.get("created_at", int(datetime.now().timestamp())),
            updated_at=data.get("updated_at", int(datetime.now().timestamp()))
        )

    def _matrix_to_dict(self, matrix: PermissionMatrix) -> Dict[str, Any]:
        """将PermissionMatrix对象转换为字典"""
        # 转换角色权限
        role_permissions = {}
        for role, perms in matrix.role_permissions.items():
            role_permissions[role] = [
                {
                    "action": perm.action.value if hasattr(perm.action, 'value') else str(perm.action),
                    "resource": perm.resource.value if hasattr(perm.resource, 'value') else str(perm.resource),
                    "conditions": perm.conditions,
                    "risk_level": perm.risk_level.value if hasattr(perm.risk_level, 'value') else str(perm.risk_level),
                    "description": perm.description
                }
                for perm in perms
            ]

        return {
            "matrix_id": matrix.matrix_id,
            "name": matrix.name,
            "description": matrix.description,
            "role_permissions": role_permissions,
            "default_policy": matrix.default_policy,
            "whitelist": matrix.whitelist,
            "blacklist": matrix.blacklist,
            "high_risk_actions": matrix.high_risk_actions,
            "version": matrix.version,
            "created_at": matrix.created_at,
            "updated_at": matrix.updated_at
        }


# 创建默认权限配置
def create_default_permissions_config() -> Dict[str, Any]:
    """创建默认权限配置"""
    return {
        "matrix_id": "default-matrix",
        "name": "默认权限矩阵",
        "description": "系统默认的权限控制矩阵",
        "role_permissions": {
            "super_admin": [
                {
                    "action": "*",
                    "resource": "*",
                    "conditions": {},
                    "risk_level": "low",
                    "description": "超级管理员拥有所有权限"
                }
            ],
            "tenant_admin": [
                {
                    "action": "read",
                    "resource": "asset",
                    "conditions": {},
                    "risk_level": "low",
                    "description": "查看资产信息"
                },
                {
                    "action": "create",
                    "resource": "asset",
                    "conditions": {},
                    "risk_level": "medium",
                    "description": "创建资产"
                },
                {
                    "action": "update",
                    "resource": "asset",
                    "conditions": {},
                    "risk_level": "medium",
                    "description": "更新资产信息"
                },
                {
                    "action": "delete",
                    "resource": "asset",
                    "conditions": {},
                    "risk_level": "high",
                    "description": "删除资产"
                },
                {
                    "action": "execute",
                    "resource": "task",
                    "conditions": {},
                    "risk_level": "medium",
                    "description": "执行任务"
                },
                {
                    "action": "read",
                    "resource": "node",
                    "conditions": {},
                    "risk_level": "low",
                    "description": "查看节点信息"
                }
            ],
            "operator": [
                {
                    "action": "read",
                    "resource": "asset",
                    "conditions": {},
                    "risk_level": "low",
                    "description": "查看资产信息"
                },
                {
                    "action": "list",
                    "resource": "asset",
                    "conditions": {},
                    "risk_level": "low",
                    "description": "列出资产"
                },
                {
                    "action": "update",
                    "resource": "task",
                    "conditions": {},
                    "risk_level": "medium",
                    "description": "更新任务状态"
                },
                {
                    "action": "execute",
                    "resource": "task",
                    "conditions": {},
                    "risk_level": "medium",
                    "description": "执行任务"
                },
                {
                    "action": "read",
                    "resource": "log",
                    "conditions": {},
                    "risk_level": "low",
                    "description": "查看日志"
                }
            ],
            "viewer": [
                {
                    "action": "read",
                    "resource": "asset",
                    "conditions": {},
                    "risk_level": "low",
                    "description": "查看资产信息"
                },
                {
                    "action": "list",
                    "resource": "asset",
                    "conditions": {},
                    "risk_level": "low",
                    "description": "列出资产"
                },
                {
                    "action": "read",
                    "resource": "task",
                    "conditions": {},
                    "risk_level": "low",
                    "description": "查看任务信息"
                },
                {
                    "action": "list",
                    "resource": "task",
                    "conditions": {},
                    "risk_level": "low",
                    "description": "列出任务"
                }
            ],
            "node": [
                {
                    "action": "heartbeat",
                    "resource": "node",
                    "conditions": {},
                    "risk_level": "low",
                    "description": "节点心跳"
                },
                {
                    "action": "status",
                    "resource": "task",
                    "conditions": {},
                    "risk_level": "low",
                    "description": "任务状态报告"
                },
                {
                    "action": "execute",
                    "resource": "task",
                    "conditions": {},
                    "risk_level": "medium",
                    "description": "执行分配的任务"
                },
                {
                    "action": "report",
                    "resource": "task",
                    "conditions": {},
                    "risk_level": "low",
                    "description": "报告任务执行结果"
                }
            ]
        },
        "default_policy": "deny",
        "whitelist": [
            "health.check",
            "system.ping",
            "node.heartbeat"
        ],
        "blacklist": [
            "system.shutdown",
            "data.delete_all",
            "*.drop.*",
            "security.bypass",
            "auth.disable"
        ],
        "high_risk_actions": [
            "delete",
            "deregister",
            "restart",
            "rollback",
            "grant",
            "revoke",
            "admin",
            "shutdown"
        ],
        "version": "1.0.0"
    }


def initialize_default_permissions(config_dir: str = "config") -> bool:
    """
    初始化默认权限配置

    Args:
        config_dir: 配置文件目录

    Returns:
        是否初始化成功
    """
    try:
        # 创建管理器
        manager = PermissionMatrixManager(config_dir)

        # 检查是否已存在默认配置
        if manager.load_matrix("default-matrix"):
            print("默认权限配置已存在")
            return True

        # 创建默认配置
        default_config = create_default_permissions_config()

        # 保存配置
        config_file = Path(config_dir) / "default-matrix.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)

        print("默认权限配置初始化完成")
        return True

    except Exception as e:
        print(f"初始化默认权限配置失败: {e}")
        return False


# 全局权限矩阵管理器实例
_global_matrix_manager: Optional[PermissionMatrixManager] = None


def get_matrix_manager() -> PermissionMatrixManager:
    """获取全局权限矩阵管理器实例"""
    global _global_matrix_manager
    if _global_matrix_manager is None:
        _global_matrix_manager = PermissionMatrixManager()
        # 初始化默认配置
        initialize_default_permissions()
    return _global_matrix_manager