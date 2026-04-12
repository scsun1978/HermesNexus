"""
HermesNexus Phase 3 - 权限模型
定义权限相关的基本数据结构和枚举
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """操作动作类型枚举"""

    # 查询操作（低风险）
    READ = "read"
    LIST = "list"
    GET = "get"
    QUERY = "query"
    DESCRIBE = "describe"

    # 修改操作（中风险）
    CREATE = "create"
    UPDATE = "update"
    MODIFY = "modify"
    CHANGE = "change"
    CONFIGURE = "configure"

    # 删除操作（高风险）
    DELETE = "delete"
    REMOVE = "remove"
    UNBIND = "unbind"
    DEREGISTER = "deregister"

    # 执行操作（中高风险）
    EXECUTE = "execute"
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    DEPLOY = "deploy"
    ROLLBACK = "rollback"

    # 管理操作（高风险）
    APPROVE = "approve"
    REJECT = "reject"
    GRANT = "grant"
    REVOKE = "revoke"
    ADMIN = "admin"

    # 节点特定操作
    HEARTBEAT = "heartbeat"
    STATUS = "status"
    REPORT = "report"

    # 通配符
    ALL = "*"  # 所有操作


class ResourceType(str, Enum):
    """资源类型枚举"""
    ASSET = "asset"  # 资产/设备
    TASK = "task"  # 任务
    NODE = "node"  # 节点
    USER = "user"  # 用户
    TENANT = "tenant"  # 租户
    REGION = "region"  # 区域
    CONFIG = "config"  # 配置
    LOG = "log"  # 日志
    AUDIT = "audit"  # 审计
    ALL = "*"  # 所有资源类型


class RiskLevel(str, Enum):
    """风险等级枚举"""
    LOW = "low"  # 低风险：查询操作
    MEDIUM = "medium"  # 中风险：修改操作
    HIGH = "high"  # 高风险：删除、关键变更


class Permission(BaseModel):
    """权限定义"""

    action: ActionType = Field(..., description="操作动作")
    resource: ResourceType = Field(..., description="资源类型")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="权限条件")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="风险等级")
    description: Optional[str] = Field(None, description="权限描述")

    class Config:
        json_schema_extra = {
            "example": {
                "action": "read",
                "resource": "asset",
                "conditions": {"tenant_id": "tenant-001"},
                "risk_level": "low",
                "description": "查询租户内的资产信息"
            }
        }


class PermissionContext(BaseModel):
    """权限上下文 - 包含进行权限检查所需的所有上下文信息"""

    # 用户身份信息
    user_id: str = Field(..., description="用户ID")
    user_type: str = Field(default="human", description="用户类型: human/node/admin")
    roles: List[str] = Field(default_factory=list, description="用户角色列表")

    # 租户和区域信息
    tenant_id: Optional[str] = Field(None, description="租户ID")
    region_id: Optional[str] = Field(None, description="区域ID")
    zone_ids: List[str] = Field(default_factory=list, description="可用区域列表")

    # 资源限制
    allowed_asset_types: List[str] = Field(default_factory=list, description="允许操作的设备类型")
    allowed_regions: List[str] = Field(default_factory=list, description="允许操作的区域")

    # 时间限制
    not_before: Optional[int] = Field(None, description="权限生效时间（Unix时间戳）")
    not_after: Optional[int] = Field(None, description="权限失效时间（Unix时间戳）")

    # 额外属性
    attributes: Dict[str, Any] = Field(default_factory=dict, description="额外的权限属性")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user-001",
                "user_type": "human",
                "roles": ["operator", "tenant_admin"],
                "tenant_id": "tenant-001",
                "region_id": "region-cn-east",
                "zone_ids": ["zone-shanghai", "zone-hangzhou"],
                "allowed_asset_types": ["server", "switch"],
                "allowed_regions": ["cn-east", "cn-south"]
            }
        }


class PermissionCheckResult(BaseModel):
    """权限检查结果"""

    allowed: bool = Field(..., description="是否允许操作")
    reason: str = Field(default="", description="拒绝原因（如果拒绝）")
    risk_level: RiskLevel = Field(..., description="操作风险等级")
    requires_approval: bool = Field(default=False, description="是否需要审批")
    missing_permissions: List[str] = Field(default_factory=list, description="缺失的权限列表")

    class Config:
        json_schema_extra = {
            "example": {
                "allowed": False,
                "reason": "用户角色 insufficient_permissions",
                "risk_level": "high",
                "requires_approval": True,
                "missing_permissions": ["asset.delete", "asset.admin"]
            }
        }


class PermissionMatrix(BaseModel):
    """权限矩阵 - 定义角色与权限的映射关系"""

    matrix_id: str = Field(..., description="权限矩阵ID")
    name: str = Field(..., description="权限矩阵名称")
    description: Optional[str] = Field(None, description="权限矩阵描述")

    # 角色到权限的映射
    role_permissions: Dict[str, List[Permission]] = Field(
        default_factory=dict,
        description="角色权限映射: role_name -> [Permission]"
    )

    # 全局策略
    default_policy: str = Field(
        default="deny",
        description="默认策略: allow(默认允许) / deny(默认拒绝)"
    )

    # 白名单和黑名单
    whitelist: List[str] = Field(
        default_factory=list,
        description="白名单：无条件允许的权限表达式"
    )
    blacklist: List[str] = Field(
        default_factory=list,
        description="黑名单：无条件拒绝的权限表达式"
    )

    # 高危动作定义
    high_risk_actions: List[str] = Field(
        default_factory=list,
        description="高风险动作列表"
    )

    # 版本控制
    version: str = Field(default="1.0.0", description="权限矩阵版本")
    created_at: int = Field(..., description="创建时间（Unix时间戳）")
    updated_at: int = Field(..., description="更新时间（Unix时间戳）")

    class Config:
        json_schema_extra = {
            "example": {
                "matrix_id": "matrix-default-001",
                "name": "默认权限矩阵",
                "description": "系统默认的权限控制矩阵",
                "role_permissions": {
                    "admin": [
                        {
                            "action": "*",
                            "resource": "*",
                            "risk_level": "low"
                        }
                    ],
                    "operator": [
                        {
                            "action": "read",
                            "resource": "asset",
                            "risk_level": "low"
                        },
                        {
                            "action": "update",
                            "resource": "task",
                            "risk_level": "medium"
                        }
                    ]
                },
                "default_policy": "deny",
                "whitelist": ["health.check"],
                "blacklist": ["system.shutdown", "data.delete_all"],
                "high_risk_actions": ["delete", "deregister", "restart", "rollback"],
                "version": "1.0.0"
            }
        }


# 内置角色定义
class BuiltInRoles:
    """内置角色常量"""

    SUPER_ADMIN = "super_admin"  # 超级管理员 - 所有权限
    TENANT_ADMIN = "tenant_admin"  # 租户管理员 - 租户内所有权限
    OPERATOR = "operator"  # 操作员 - 常规运维操作
    VIEWER = "viewer"  # 查看者 - 只读权限
    NODE = "node"  # 节点 - 节点身份的权限
    AUDITOR = "auditor"  # 审计员 - 审计日志查看权限


# 常用权限组合
class CommonPermissions:
    """常用权限组合"""

    # 只读权限
    READ_ONLY = [
        Permission(action=ActionType.READ, resource=ResourceType.ASSET, risk_level=RiskLevel.LOW),
        Permission(action=ActionType.LIST, resource=ResourceType.ASSET, risk_level=RiskLevel.LOW),
        Permission(action=ActionType.READ, resource=ResourceType.TASK, risk_level=RiskLevel.LOW),
        Permission(action=ActionType.LIST, resource=ResourceType.TASK, risk_level=RiskLevel.LOW),
    ]

    # 操作员权限
    OPERATOR = [
        Permission(action=ActionType.READ, resource=ResourceType.ASSET, risk_level=RiskLevel.LOW),
        Permission(action=ActionType.LIST, resource=ResourceType.ASSET, risk_level=RiskLevel.LOW),
        Permission(action=ActionType.UPDATE, resource=ResourceType.TASK, risk_level=RiskLevel.MEDIUM),
        Permission(action=ActionType.EXECUTE, resource=ResourceType.TASK, risk_level=RiskLevel.MEDIUM),
        Permission(action=ActionType.READ, resource=ResourceType.LOG, risk_level=RiskLevel.LOW),
    ]

    # 管理员权限
    ADMIN = [
        Permission(action=ActionType.READ, resource=ResourceType.ASSET, risk_level=RiskLevel.LOW),
        Permission(action=ActionType.CREATE, resource=ResourceType.ASSET, risk_level=RiskLevel.MEDIUM),
        Permission(action=ActionType.UPDATE, resource=ResourceType.ASSET, risk_level=RiskLevel.MEDIUM),
        Permission(action=ActionType.DELETE, resource=ResourceType.ASSET, risk_level=RiskLevel.HIGH),
        Permission(action=ActionType.EXECUTE, resource=ResourceType.TASK, risk_level=RiskLevel.MEDIUM),
        Permission(action=ActionType.START, resource=ResourceType.TASK, risk_level=RiskLevel.MEDIUM),
        Permission(action=ActionType.STOP, resource=ResourceType.TASK, risk_level=RiskLevel.MEDIUM),
        Permission(action=ActionType.ADMIN, resource=ResourceType.CONFIG, risk_level=RiskLevel.HIGH),
    ]

    # 节点权限
    NODE = [
        Permission(action=ActionType.HEARTBEAT, resource=ResourceType.NODE, risk_level=RiskLevel.LOW),
        Permission(action=ActionType.STATUS, resource=ResourceType.TASK, risk_level=RiskLevel.LOW),
        Permission(action=ActionType.EXECUTE, resource=ResourceType.TASK, risk_level=RiskLevel.MEDIUM),
        Permission(action=ActionType.REPORT, resource=ResourceType.TASK, risk_level=RiskLevel.LOW),
    ]