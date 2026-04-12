"""
HermesNexus Phase 2 - SQLAlchemy ORM Models
数据库ORM模型定义
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import declarative_base

# 创建基础模型类
Base = declarative_base()


class AssetModel(Base):
    """资产表ORM模型"""

    __tablename__ = "assets"

    # 主键
    asset_id = Column(String(64), primary_key=True)

    # 基本字段
    name = Column(String(255), nullable=False)
    asset_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)

    # 创建信息
    created_by = Column(String(128), nullable=True)

    # 元数据（JSON格式）
    meta_data = Column("metadata", JSON, nullable=True)

    # 时间字段
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    last_heartbeat = Column("last_heartbeat_at", DateTime, nullable=True)

    # 索引
    __table_args__ = (
        Index("idx_assets_type", "asset_type"),
        Index("idx_assets_status", "status"),
        Index("idx_assets_created_at", "created_at"),
        Index("idx_assets_updated_at", "updated_at"),
        Index("idx_assets_type_status", "asset_type", "status"),
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "asset_type": self.asset_type,
            "status": self.status,
            "description": self.description,
            "created_by": self.created_by,
            "metadata": self.meta_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_heartbeat": (
                self.last_heartbeat.isoformat() if self.last_heartbeat else None
            ),
        }


class NodeModel(Base):
    """节点表ORM模型 - Phase 3: 节点身份管理"""

    __tablename__ = "nodes"

    # 主键
    node_id = Column(String(64), primary_key=True)

    # 基本字段
    node_name = Column(String(255), nullable=False)
    node_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)

    # 多租户字段 (Phase 3)
    tenant_id = Column(String(64), nullable=False)
    region_id = Column(String(64), nullable=False)

    # 认证信息
    auth_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    public_key = Column(Text, nullable=True)

    # 能力信息
    capabilities = Column(JSON, nullable=True)
    max_concurrent_tasks = Column(Integer, nullable=False, default=3)

    # 关联关系
    managed_devices = Column(Text, nullable=True)  # 逗号分隔的设备ID列表
    assigned_tasks = Column(Text, nullable=True)  # 逗号分隔的任务ID列表

    # 位置和标签
    location = Column(String(255), nullable=True)
    tags = Column(Text, nullable=True)  # 逗号分隔的标签列表

    # 元数据
    node_metadata = Column("metadata", JSON, nullable=True)

    # 创建信息
    created_by = Column(String(128), nullable=True)

    # 时间字段
    registered_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    last_heartbeat = Column(DateTime, nullable=True)

    # 索引
    __table_args__ = (
        Index("idx_nodes_type", "node_type"),
        Index("idx_nodes_status", "status"),
        Index("nodes_registered_at", "registered_at"),
        Index("idx_nodes_last_heartbeat", "last_heartbeat"),
        Index("idx_nodes_type_status", "node_type", "status"),
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "node_type": self.node_type,
            "status": self.status,
            "description": self.description,
            "auth_token": self.auth_token,
            "token_expires_at": (
                self.token_expires_at.isoformat() if self.token_expires_at else None
            ),
            "capabilities": self.capabilities,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "managed_devices": (
                self.managed_devices.split(",") if self.managed_devices else []
            ),
            "assigned_tasks": (
                self.assigned_tasks.split(",") if self.assigned_tasks else []
            ),
            "location": self.location,
            "tags": self.tags.split(",") if self.tags else [],
            "created_by": self.created_by,
            "registered_at": (
                self.registered_at.isoformat() if self.registered_at else None
            ),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_heartbeat": (
                self.last_heartbeat.isoformat() if self.last_heartbeat else None
            ),
        }


class TaskModel(Base):
    """任务表ORM模型"""

    __tablename__ = "tasks"

    # 主键
    task_id = Column(String(64), primary_key=True)

    # 基本字段
    name = Column(String(255), nullable=False)
    task_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    priority = Column(String(50), nullable=False)

    # 关联字段
    target_asset_id = Column(
        String(64), ForeignKey("assets.asset_id", ondelete="SET NULL"), nullable=False
    )
    assigned_node_id = Column(String(64), nullable=True)

    # 任务参数
    command = Column(Text, nullable=True)
    script_content = Column(Text, nullable=True)
    timeout = Column("timeout_seconds", Integer, nullable=False, default=30)
    description = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=False)

    # 执行结果（JSON格式）
    result_data = Column("result", JSON, nullable=True)

    # 时间字段
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # 索引
    __table_args__ = (
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_type", "task_type"),
        Index("idx_tasks_priority", "priority"),
        Index("idx_tasks_asset", "target_asset_id"),
        Index("idx_tasks_node", "assigned_node_id"),
        Index("idx_tasks_created_at", "created_at"),
        Index("idx_tasks_updated_at", "updated_at"),
        Index("idx_tasks_status_priority", "status", "priority"),
        Index("idx_tasks_asset_status", "target_asset_id", "status"),
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "task_type": self.task_type,
            "status": self.status,
            "priority": self.priority,
            "target_asset_id": self.target_asset_id,
            "assigned_node_id": self.assigned_node_id,
            "command": self.command,
            "script_content": self.script_content,
            "timeout_seconds": self.timeout,
            "description": self.description,
            "created_by": self.created_by,
            "result": self.result_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


class AuditLogModel(Base):
    """审计日志表ORM模型"""

    __tablename__ = "audit_logs"

    # 主键
    audit_id = Column(String(64), primary_key=True)

    # 基本字段
    action = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    level = Column(String(50), nullable=False)

    # 操作者信息
    actor = Column(String(255), nullable=True)

    # 目标信息
    target_type = Column(String(50), nullable=True)
    target_id = Column(String(255), nullable=True)

    # 日志内容
    message = Column(Text, nullable=False)

    # 元数据（JSON格式）
    meta_data = Column("metadata", JSON, nullable=True)

    # 时间字段
    created_at = Column(DateTime, nullable=False)

    # 索引
    __table_args__ = (
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_category", "category"),
        Index("idx_audit_logs_level", "level"),
        Index("idx_audit_logs_actor", "actor"),
        Index("idx_audit_logs_target", "target_type", "target_id"),
        Index("idx_audit_logs_created_at", "created_at"),
        Index("idx_audit_logs_category_created", "category", "created_at"),
    )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "audit_id": self.audit_id,
            "action": self.action,
            "category": self.category,
            "level": self.level,
            "actor": self.actor,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "message": self.message,
            "metadata": self.meta_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
