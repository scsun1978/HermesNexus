"""
HermesNexus Phase 3 - 节点身份DAO
节点身份的数据访问对象
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from shared.dao.base_dao import BaseDAO
from shared.database.models import NodeModel
from shared.models.node import NodeIdentity, NodeStatus


class NodeDAO(BaseDAO):
    """节点身份数据访问对象"""

    def insert(self, node: NodeIdentity) -> NodeIdentity:
        """
        插入节点身份

        Args:
            node: 节点身份对象

        Returns:
            插入后的节点对象
        """
        session = self._get_session()

        try:
            # 创建ORM模型实例
            node_model = NodeModel(
                node_id=node.node_id,
                node_name=node.node_name,
                node_type=node.node_type.value,
                tenant_id=node.tenant_id,
                region_id=node.region_id,
                status=node.status.value,
                auth_token=node.auth_token,
                token_expires_at=node.token_expires_at,
                public_key=node.public_key,
                capabilities=node.capabilities,
                max_concurrent_tasks=node.max_concurrent_tasks,
                registered_at=node.registered_at,
                last_heartbeat=node.last_heartbeat,
                managed_devices=",".join(node.managed_devices) if node.managed_devices else None,
                assigned_tasks=",".join(node.assigned_tasks) if node.assigned_tasks else None,
                description=node.description,
                location=node.location,
                tags=",".join(node.tags) if node.tags else None,
                node_metadata=node.node_metadata,
                created_by=node.created_by,
                updated_at=node.updated_at
            )

            # 插入数据库
            session.add(node_model)
            session.commit()
            session.refresh(node_model)

            return node

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to insert node: {e}")
        finally:
            session.close()

    def select_by_id(self, node_id: str) -> Optional[NodeIdentity]:
        """
        按ID查询节点身份

        Args:
            node_id: 节点ID

        Returns:
            节点身份对象，如果不存在则返回None
        """
        session = self._get_session()

        try:
            # 查询数据库
            node_model = session.query(NodeModel).filter(
                NodeModel.node_id == node_id
            ).first()

            if not node_model:
                return None

            # 转换为节点身份对象
            return self._model_to_node_identity(node_model)

        finally:
            session.close()

    def update(self, node: NodeIdentity) -> NodeIdentity:
        """
        更新节点身份

        Args:
            node: 节点身份对象

        Returns:
            更新后的节点对象
        """
        session = self._get_session()

        try:
            # 查询现有节点
            node_model = session.query(NodeModel).filter(
                NodeModel.node_id == node.node_id
            ).first()

            if not node_model:
                raise ValueError(f"Node not found: {node.node_id}")

            # 更新字段
            node_model.node_name = node.node_name
            node_model.status = node.status.value
            node_model.auth_token = node.auth_token
            node_model.token_expires_at = node.token_expires_at
            node_model.last_heartbeat = node.last_heartbeat
            node_model.assigned_tasks = ",".join(node.assigned_tasks) if node.assigned_tasks else None
            node_model.updated_at = datetime.utcnow()

            # 提交更改
            session.commit()
            session.refresh(node_model)

            return node

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to update node: {e}")
        finally:
            session.close()

    def list(self, filters: Dict[str, Any] = None, limit: int = None,
            offset: int = None, order_by: str = None) -> List[NodeIdentity]:
        """
        查询节点列表

        Args:
            filters: 过滤条件
            limit: 返回数量限制
            offset: 偏移量
            order_by: 排序字段

        Returns:
            节点身份列表
        """
        session = self._get_session()

        try:
            query = session.query(NodeModel)

            # 应用过滤条件
            if filters:
                if "node_id" in filters:
                    query = query.filter(NodeModel.node_id == filters["node_id"])
                if "status" in filters:
                    if isinstance(filters["status"], list):
                        query = query.filter(NodeModel.status.in_(filters["status"]))
                    else:
                        query = query.filter(NodeModel.status == filters["status"])
                if "node_type" in filters:
                    query = query.filter(NodeModel.node_type == filters["node_type"])

            # 排序
            if order_by:
                if order_by.startswith("-"):
                    query = query.order_by(NodeModel.created_at.desc())
                else:
                    query = query.order_by(NodeModel.created_at.asc())

            # 分页
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            # 执行查询
            node_models = query.all()

            # 转换为节点身份对象
            return [self._model_to_node_identity(model) for model in node_models]

        finally:
            session.close()

    def count(self, filters: Dict[str, Any] = None) -> int:
        """
        统计节点数量

        Args:
            filters: 过滤条件

        Returns:
            节点数量
        """
        session = self._get_session()

        try:
            query = session.query(NodeModel)

            # 应用过滤条件
            if filters:
                if "status" in filters:
                    if isinstance(filters["status"], list):
                        query = query.filter(NodeModel.status.in_(filters["status"]))
                    else:
                        query = query.filter(NodeModel.status == filters["status"])

            return query.count()

        finally:
            session.close()

    def delete(self, node_id: str) -> bool:
        """
        删除节点身份

        Args:
            node_id: 节点ID

        Returns:
            是否删除成功
        """
        session = self._get_session()

        try:
            # 查询节点
            node_model = session.query(NodeModel).filter(
                NodeModel.node_id == node_id
            ).first()

            if not node_model:
                return False

            # 删除节点
            session.delete(node_model)
            session.commit()

            return True

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to delete node: {e}")
        finally:
            session.close()

    def _model_to_node_identity(self, model: NodeModel) -> NodeIdentity:
        """
        将ORM模型转换为节点身份对象

        Args:
            model: ORM模型

        Returns:
            节点身份对象
        """
        from shared.models.node import NodeType, NodeIdentity

        return NodeIdentity(
            node_id=model.node_id,
            node_name=model.node_name,
            node_type=NodeType(model.node_type),
            tenant_id=model.tenant_id,
            region_id=model.region_id,
            status=NodeStatus(model.status),
            auth_token=model.auth_token,
            token_expires_at=model.token_expires_at,
            public_key=model.public_key,
            capabilities=model.capabilities if isinstance(model.capabilities, dict) else {},
            max_concurrent_tasks=model.max_concurrent_tasks or 3,
            registered_at=model.registered_at,
            last_heartbeat=model.last_heartbeat,
            managed_devices=model.managed_devices.split(",") if model.managed_devices else [],
            assigned_tasks=model.assigned_tasks.split(",") if model.assigned_tasks else [],
            description=model.description,
            location=model.location,
            tags=model.tags.split(",") if model.tags else [],
            node_metadata=model.node_metadata if isinstance(model.node_metadata, dict) else {},
            created_by=model.created_by,
            created_at=model.registered_at,  # Use registered_at as created_at
            updated_at=model.updated_at
        )