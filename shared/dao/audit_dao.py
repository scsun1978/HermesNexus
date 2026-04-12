"""
HermesNexus Phase 2 - AuditLog DAO
审计日志数据访问对象
"""

from typing import Optional, List, Dict, Any
from sqlalchemy import or_, desc

from shared.dao.base_dao import BaseDAO
from shared.database.models import AuditLogModel
from shared.models.audit import AuditLog


class AuditDAO(BaseDAO):
    """审计日志数据访问对象"""

    def insert(self, audit_log: AuditLog) -> AuditLog:
        """
        插入审计日志

        Args:
            audit_log: 审计日志对象

        Returns:
            插入后的审计日志对象
        """
        session = self._get_session()

        try:
            # 创建ORM模型实例
            meta_data = dict(audit_log.details or {})
            if audit_log.related_task_id:
                meta_data.setdefault("related_task_id", audit_log.related_task_id)
            if audit_log.related_node_id:
                meta_data.setdefault("related_node_id", audit_log.related_node_id)
            if audit_log.related_asset_id:
                meta_data.setdefault("related_asset_id", audit_log.related_asset_id)

            audit_model = AuditLogModel(
                audit_id=audit_log.audit_id,
                action=audit_log.action,
                category=audit_log.category,
                level=audit_log.level,
                actor=audit_log.actor,
                target_type=audit_log.target_type,
                target_id=audit_log.target_id,
                message=audit_log.message,
                meta_data=meta_data,
                created_at=audit_log.created_at,
            )

            # 插入数据库
            session.add(audit_model)
            session.commit()
            session.refresh(audit_model)

            # 返回审计日志对象
            return audit_log

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to insert audit log: {e}")
        finally:
            session.close()

    def select_by_id(self, audit_id: str) -> Optional[AuditLog]:
        """
        按ID查询审计日志

        Args:
            audit_id: 审计日志ID

        Returns:
            审计日志对象，如果不存在则返回None
        """
        session = self._get_session()

        try:
            # 查询数据库
            audit_model = (
                session.query(AuditLogModel)
                .filter(AuditLogModel.audit_id == audit_id)
                .first()
            )

            if not audit_model:
                return None

            # 转换为审计日志对象
            return self._model_to_audit_log(audit_model)

        finally:
            session.close()

    def update(self, audit_log: AuditLog) -> AuditLog:
        """
        更新审计日志（通常不需要，审计日志不允许更新）

        Args:
            audit_log: 审计日志对象

        Returns:
            更新后的审计日志对象
        """
        # 审计日志通常不允许更新
        raise NotImplementedError("Audit logs cannot be updated")

    def delete(self, audit_id: str) -> bool:
        """
        删除审计日志（通常不允许，审计日志不可删除）

        Args:
            audit_id: 审计日志ID

        Returns:
            是否删除成功
        """
        # 审计日志通常不允许删除
        raise NotImplementedError("Audit logs cannot be deleted")

    def list(
        self,
        filters: Dict[str, Any] = None,
        limit: int = None,
        offset: int = None,
        order_by: str = None,
    ) -> List[AuditLog]:
        """
        查询审计日志列表

        Args:
            filters: 过滤条件字典
            limit: 返回数量限制
            offset: 偏移量
            order_by: 排序字段

        Returns:
            审计日志列表
        """
        session = self._get_session()

        try:
            # 构建查询
            query = session.query(AuditLogModel)

            # 应用过滤条件
            if filters:
                if "action" in filters:
                    query = query.filter(AuditLogModel.action == filters["action"])
                if "category" in filters:
                    query = query.filter(AuditLogModel.category == filters["category"])
                if "level" in filters:
                    query = query.filter(AuditLogModel.level == filters["level"])
                if "actor" in filters:
                    query = query.filter(AuditLogModel.actor == filters["actor"])
                if "target_type" in filters:
                    query = query.filter(
                        AuditLogModel.target_type == filters["target_type"]
                    )
                if "target_id" in filters:
                    query = query.filter(
                        AuditLogModel.target_id == filters["target_id"]
                    )
                if "start_time" in filters:
                    query = query.filter(
                        AuditLogModel.created_at >= filters["start_time"]
                    )
                if "end_time" in filters:
                    query = query.filter(
                        AuditLogModel.created_at <= filters["end_time"]
                    )
                if "search" in filters:
                    search_term = f"%{filters['search']}%"
                    query = query.filter(
                        or_(
                            AuditLogModel.message.like(search_term),
                            AuditLogModel.actor.like(search_term),
                        )
                    )

            # 应用排序（默认按创建时间倒序）
            if order_by:
                if order_by.startswith("-"):
                    field = order_by[1:]
                    query = query.order_by(desc(getattr(AuditLogModel, field)))
                else:
                    query = query.order_by(getattr(AuditLogModel, order_by))
            else:
                # 默认按创建时间倒序
                query = query.order_by(desc(AuditLogModel.created_at))

            # 应用分页
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)

            # 执行查询
            audit_models = query.all()

            # 转换为审计日志对象列表
            return [self._model_to_audit_log(model) for model in audit_models]

        finally:
            session.close()

    def count(self, filters: Dict[str, Any] = None) -> int:
        """
        统计审计日志数量

        Args:
            filters: 过滤条件字典

        Returns:
            审计日志数量
        """
        session = self._get_session()

        try:
            # 构建查询
            query = session.query(AuditLogModel)

            # 应用过滤条件
            if filters:
                if "action" in filters:
                    query = query.filter(AuditLogModel.action == filters["action"])
                if "category" in filters:
                    query = query.filter(AuditLogModel.category == filters["category"])
                if "level" in filters:
                    query = query.filter(AuditLogModel.level == filters["level"])
                if "actor" in filters:
                    query = query.filter(AuditLogModel.actor == filters["actor"])
                if "target_type" in filters:
                    query = query.filter(
                        AuditLogModel.target_type == filters["target_type"]
                    )

            # 统计数量
            return query.count()

        finally:
            session.close()

    def query_by_task(self, task_id: str, limit: int = None) -> List[AuditLog]:
        """
        查询特定任务的审计日志

        Args:
            task_id: 任务ID
            limit: 返回数量限制

        Returns:
            审计日志列表
        """
        logs = self.list(order_by="-created_at")
        matched = []
        for log in logs:
            meta = log.details or {}
            if (
                (log.target_type == "task" and log.target_id == task_id)
                or log.related_task_id == task_id
                or meta.get("related_task_id") == task_id
                or meta.get("task_id") == task_id
            ):
                matched.append(log)
        return matched[:limit] if limit else matched

    def query_by_node(self, node_id: str, limit: int = None) -> List[AuditLog]:
        """
        查询特定节点的审计日志

        Args:
            node_id: 节点ID
            limit: 返回数量限制

        Returns:
            审计日志列表
        """
        logs = self.list(order_by="-created_at")
        matched = []
        for log in logs:
            meta = log.details or {}
            if (
                (log.target_type == "node" and log.target_id == node_id)
                or log.related_node_id == node_id
                or meta.get("related_node_id") == node_id
                or meta.get("node_id") == node_id
            ):
                matched.append(log)
        return matched[:limit] if limit else matched

    def query_by_asset(self, asset_id: str, limit: int = None) -> List[AuditLog]:
        """
        查询特定资产的审计日志

        Args:
            asset_id: 资产ID
            limit: 返回数量限制

        Returns:
            审计日志列表
        """
        logs = self.list(order_by="-created_at")
        matched = []
        for log in logs:
            meta = log.details or {}
            if (
                (log.target_type == "asset" and log.target_id == asset_id)
                or log.related_asset_id == asset_id
                or meta.get("related_asset_id") == asset_id
                or meta.get("target_asset_id") == asset_id
                or meta.get("asset_id") == asset_id
            ):
                matched.append(log)
        return matched[:limit] if limit else matched

    def _model_to_audit_log(self, model: AuditLogModel) -> AuditLog:
        """
        将ORM模型转换为审计日志对象

        Args:
            model: ORM模型

        Returns:
            审计日志对象
        """
        # 构建审计日志对象
        meta_data = model.meta_data or {}
        return AuditLog(
            audit_id=model.audit_id,
            action=model.action,
            category=model.category,
            level=model.level,
            actor=model.actor,
            target_type=model.target_type,
            target_id=model.target_id,
            related_task_id=meta_data.get("related_task_id"),
            related_node_id=meta_data.get("related_node_id"),
            related_asset_id=meta_data.get("related_asset_id"),
            message=model.message,
            details=meta_data,
            created_at=model.created_at,
        )

    def select_by_ids(self, audit_ids: List[str]) -> List[AuditLog]:
        """
        批量查询审计日志 - 解决N+1查询问题

        Args:
            audit_ids: 审计日志ID列表

        Returns:
            审计日志对象列表
        """
        if not audit_ids:
            return []

        session = self._get_session()

        try:
            # 批量查询 - 一次查询获取所有数据
            audit_models = (
                session.query(AuditLogModel)
                .filter(AuditLogModel.audit_id.in_(audit_ids))
                .all()
            )

            # 转换为审计日志对象列表
            return [self._model_to_audit_log(model) for model in audit_models]

        finally:
            session.close()

    def insert_batch(self, audit_logs: List[AuditLog]) -> List[AuditLog]:
        """
        批量插入审计日志 - 提升插入性能

        Args:
            audit_logs: 审计日志对象列表

        Returns:
            插入后的审计日志对象列表
        """
        if not audit_logs:
            return []

        session = self._get_session()

        try:
            # 创建ORM模型实例列表
            audit_models = []
            for audit_log in audit_logs:
                # 处理metadata
                meta_data = audit_log.details or {}

                audit_model = AuditLogModel(
                    audit_id=audit_log.audit_id,
                    action=audit_log.action,
                    category=audit_log.category,
                    level=audit_log.level,
                    actor=audit_log.actor,
                    target_type=audit_log.target_type,
                    target_id=audit_log.target_id,
                    message=audit_log.message,
                    meta_data=meta_data,
                    created_at=audit_log.created_at,
                )
                audit_models.append(audit_model)

            # 批量插入 - 减少数据库往返次数
            session.add_all(audit_models)
            session.commit()

            return audit_logs

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to batch insert audit logs: {e}")
        finally:
            session.close()
