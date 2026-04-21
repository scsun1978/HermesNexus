"""
HermesNexus Phase 2 - Asset DAO
资产数据访问对象
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import or_

from shared.dao.base_dao import BaseDAO
from shared.database.models import AssetModel
from shared.models.asset import Asset


class AssetDAO(BaseDAO):
    """资产数据访问对象"""

    def insert(self, asset: Asset) -> Asset:
        """
        插入资产

        Args:
            asset: 资产对象

        Returns:
            插入后的资产对象
        """
        session = self._get_session()

        try:
            # 创建ORM模型实例
            asset_model = AssetModel(
                asset_id=asset.asset_id,
                name=asset.name,
                asset_type=asset.asset_type,
                status=asset.status,
                description=asset.description,
                created_by=asset.created_by,
                meta_data=asset.metadata.dict() if asset.metadata else None,
                created_at=asset.created_at,
                updated_at=asset.updated_at,
                last_heartbeat=asset.last_heartbeat,
            )

            # 插入数据库
            session.add(asset_model)
            session.commit()
            session.refresh(asset_model)

            # 返回资产对象
            return asset

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to insert asset: {e}")
        finally:
            session.close()

    def select_by_id(self, asset_id: str) -> Optional[Asset]:
        """
        按ID查询资产

        Args:
            asset_id: 资产ID

        Returns:
            资产对象，如果不存在则返回None
        """
        session = self._get_session()

        try:
            # 查询数据库
            asset_model = session.query(AssetModel).filter(AssetModel.asset_id == asset_id).first()

            if not asset_model:
                return None

            # 转换为资产对象
            return self._model_to_asset(asset_model)

        finally:
            session.close()

    def update(self, asset: Asset) -> Asset:
        """
        更新资产

        Args:
            asset: 资产对象

        Returns:
            更新后的资产对象
        """
        session = self._get_session()

        try:
            # 查询现有资产
            asset_model = (
                session.query(AssetModel).filter(AssetModel.asset_id == asset.asset_id).first()
            )

            if not asset_model:
                raise ValueError(f"Asset not found: {asset.asset_id}")

            # 更新字段
            asset_model.name = asset.name
            asset_model.asset_type = asset.asset_type
            asset_model.status = asset.status
            asset_model.description = asset.description
            asset_model.created_by = asset.created_by
            asset_model.meta_data = asset.metadata.dict() if asset.metadata else None
            asset_model.updated_at = datetime.utcnow()
            if asset.last_heartbeat:
                asset_model.last_heartbeat = asset.last_heartbeat

            # 提交更改
            session.commit()
            session.refresh(asset_model)

            return asset

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to update asset: {e}")
        finally:
            session.close()

    def delete(self, asset_id: str) -> bool:
        """
        删除资产

        Args:
            asset_id: 资产ID

        Returns:
            是否删除成功
        """
        session = self._get_session()

        try:
            # 查询并删除资产
            asset_model = session.query(AssetModel).filter(AssetModel.asset_id == asset_id).first()

            if not asset_model:
                return False

            session.delete(asset_model)
            session.commit()

            return True

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to delete asset: {e}")
        finally:
            session.close()

    def list(
        self,
        filters: Dict[str, Any] = None,
        limit: int = None,
        offset: int = None,
        order_by: str = None,
    ) -> List[Asset]:
        """
        查询资产列表

        Args:
            filters: 过滤条件字典
            limit: 返回数量限制
            offset: 偏移量
            order_by: 排序字段

        Returns:
            资产列表
        """
        session = self._get_session()

        try:
            # 构建查询
            query = session.query(AssetModel)

            # 应用过滤条件
            if filters:
                if "asset_type" in filters:
                    query = query.filter(AssetModel.asset_type == filters["asset_type"])
                if "status" in filters:
                    query = query.filter(AssetModel.status == filters["status"])
                if "search" in filters:
                    search_term = f"%{filters['search']}%"
                    query = query.filter(
                        or_(
                            AssetModel.name.like(search_term),
                            AssetModel.description.like(search_term),
                        )
                    )

            # 应用排序
            if order_by:
                if order_by.startswith("-"):
                    # 降序
                    field = order_by[1:]
                    query = query.order_by(getattr(AssetModel, field).desc())
                else:
                    # 升序
                    query = query.order_by(getattr(AssetModel, order_by))

            # 应用分页
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)

            # 执行查询
            asset_models = query.all()

            # 转换为资产对象列表
            return [self._model_to_asset(model) for model in asset_models]

        finally:
            session.close()

    def count(self, filters: Dict[str, Any] = None) -> int:
        """
        统计资产数量

        Args:
            filters: 过滤条件字典

        Returns:
            资产数量
        """
        session = self._get_session()

        try:
            # 构建查询
            query = session.query(AssetModel)

            # 应用过滤条件
            if filters:
                if "asset_type" in filters:
                    query = query.filter(AssetModel.asset_type == filters["asset_type"])
                if "status" in filters:
                    query = query.filter(AssetModel.status == filters["status"])

            # 统计数量
            return query.count()

        finally:
            session.close()

    def select_by_ids(self, asset_ids: List[str]) -> List[Asset]:
        """
        批量查询资产 - 解决N+1查询问题

        Args:
            asset_ids: 资产ID列表

        Returns:
            资产对象列表
        """
        if not asset_ids:
            return []

        session = self._get_session()

        try:
            # 批量查询 - 一次查询获取所有数据
            asset_models = (
                session.query(AssetModel).filter(AssetModel.asset_id.in_(asset_ids)).all()
            )

            # 转换为资产对象列表
            return [self._model_to_asset(model) for model in asset_models]

        finally:
            session.close()

    def insert_batch(self, assets: List[Asset]) -> List[Asset]:
        """
        批量插入资产 - 提升插入性能

        Args:
            assets: 资产对象列表

        Returns:
            插入后的资产对象列表
        """
        if not assets:
            return []

        session = self._get_session()

        try:
            # 创建ORM模型实例列表
            asset_models = []
            for asset in assets:
                asset_model = AssetModel(
                    asset_id=asset.asset_id,
                    name=asset.name,
                    asset_type=asset.asset_type,
                    status=asset.status,
                    description=asset.description,
                    meta_data=asset.metadata.dict() if asset.metadata else None,
                    created_at=asset.created_at,
                    updated_at=asset.updated_at,
                    last_heartbeat=asset.last_heartbeat,
                )
                asset_models.append(asset_model)

            # 批量插入 - 减少数据库往返次数
            session.add_all(asset_models)
            session.commit()

            return assets

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to batch insert assets: {e}")
        finally:
            session.close()

    def update_batch(self, assets: List[Asset]) -> List[Asset]:
        """
        批量更新资产 - 提升更新性能

        Args:
            assets: 资产对象列表

        Returns:
            更新后的资产对象列表
        """
        if not assets:
            return []

        session = self._get_session()

        try:
            updated_assets = []
            current_time = datetime.utcnow()

            for asset in assets:
                # 查询并更新每个资产
                asset_model = (
                    session.query(AssetModel).filter(AssetModel.asset_id == asset.asset_id).first()
                )

                if asset_model:
                    # 更新字段
                    asset_model.name = asset.name
                    asset_model.asset_type = asset.asset_type
                    asset_model.status = asset.status
                    asset_model.description = asset.description
                    asset_model.meta_data = asset.metadata.dict() if asset.metadata else None
                    asset_model.updated_at = current_time
                    if asset.last_heartbeat:
                        asset_model.last_heartbeat = asset.last_heartbeat

                    updated_assets.append(asset)

            # 批量提交 - 减少事务开销
            session.commit()

            return updated_assets

        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to batch update assets: {e}")
        finally:
            session.close()

    def _model_to_asset(self, model: AssetModel) -> Asset:
        """
        将ORM模型转换为资产对象

        Args:
            model: ORM模型

        Returns:
            资产对象
        """
        from shared.models.asset import AssetMetadata

        # 构建metadata对象
        metadata = None
        if model.meta_data:
            metadata = AssetMetadata(**model.meta_data)

        # 构建资产对象
        return Asset(
            asset_id=model.asset_id,
            name=model.name,
            asset_type=model.asset_type,
            status=model.status,
            description=model.description,
            metadata=metadata,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_heartbeat=model.last_heartbeat,
        )
