"""
HermesNexus Phase 2 - Asset Service (Database Version)
资产管理业务逻辑层 - 数据库版本
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import math
from shared.models.asset import (
    Asset, AssetCreateRequest, AssetUpdateRequest,
    AssetQueryParams, AssetListResponse, AssetStats,
    AssetType, AssetStatus
)
from shared.models.enums import validate_state_transition
from shared.dao.asset_dao import AssetDAO
from shared.models.audit import AuditAction, AuditCategory, EventLevel, AuditLogCreateRequest


class AssetService:
    """资产管理服务 - 数据库版本"""

    def __init__(self, database=None):
        """
        初始化资产服务

        Args:
            database: 数据库实例
        """
        self.database = database

        # 如果有数据库，使用DAO；否则使用内存存储（向后兼容）
        if database:
            self.asset_dao = AssetDAO(database)
            self._assets: Optional[Dict[str, Asset]] = None  # 不使用内存存储
        else:
            self.asset_dao = None
            self._assets: Dict[str, Asset] = {}  # 内存存储（Phase 2 MVP兼容）

    def create_asset(self, request, created_by: str = None) -> Asset:
        """
        创建资产

        Args:
            request: 资产创建请求或完整 Asset 对象
            created_by: 创建者用户ID（可选）

        Returns:
            创建的资产

        Raises:
            ValueError: 如果资产ID已存在
        """
        if isinstance(request, Asset):
            asset = request
            asset_id = asset.asset_id
            # 确保created_by字段有值
            if asset.created_by is None:
                asset.created_by = created_by or "system"
            # 如果显式提供了created_by参数，覆盖Asset对象的值
            elif created_by is not None:
                asset.created_by = created_by
        else:
            # 生成或使用提供的资产ID
            asset_id = request.asset_id or f"asset-{uuid.uuid4().hex[:8]}"

            asset = Asset(
                asset_id=asset_id,
                name=request.name,
                asset_type=request.asset_type,
                status=AssetStatus.REGISTERED,
                metadata=getattr(request, "metadata", None),
                description=request.description,
                created_by=created_by,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

        # 检查ID是否已存在
        if self.asset_dao:
            existing = self.asset_dao.select_by_id(asset_id)
            if existing:
                raise ValueError(f"Asset with ID '{asset_id}' already exists")
        else:
            if asset_id in self._assets:
                raise ValueError(f"Asset with ID '{asset_id}' already exists")

        # 保存资产
        if self.asset_dao:
            saved = self.asset_dao.insert(asset)
        else:
            self._assets[asset_id] = asset
            saved = asset

        self._audit_asset_event(saved, AuditAction.ASSET_REGISTERED, "Asset registered")
        return saved

    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """
        获取资产详情

        Args:
            asset_id: 资产ID

        Returns:
            资产对象，如果不存在则返回 None
        """
        if self.asset_dao:
            return self.asset_dao.select_by_id(asset_id)
        else:
            return self._assets.get(asset_id)

    def update_asset(self, asset_or_id, request: AssetUpdateRequest = None) -> Optional[Asset]:
        """
        更新资产

        Args:
            asset_or_id: 资产对象或资产ID（兼容两种调用方式）
            request: 更新请求（当第一个参数是ID时必需）

        Returns:
            更新后的资产，如果不存在则返回 None

        Raises:
            ValueError: 如果状态转换不合法
        """
        # 兼容两种调用方式
        if isinstance(asset_or_id, Asset):
            # 第一个参数是Asset对象
            asset = asset_or_id
            asset_id = asset.asset_id
            # 从Asset对象构建AssetUpdateRequest
            if request is None:
                from shared.models.asset import AssetUpdateRequest
                request = AssetUpdateRequest(
                    name=asset.name,
                    description=asset.description,
                    status=asset.status,
                    metadata=asset.metadata
                )
        else:
            # 第一个参数是asset_id
            asset_id = asset_or_id
            if request is None:
                raise ValueError("request parameter is required when asset_id is provided")

        if self.asset_dao:
            # 使用数据库
            existing_asset = self.asset_dao.select_by_id(asset_id)
            if not existing_asset:
                return None

            # 如果传入的是完整Asset对象，直接更新
            if isinstance(asset_or_id, Asset):
                # 验证状态转换
                if asset.status != existing_asset.status:
                    if not asset.status.can_transition_to(existing_asset.status):
                        raise ValueError(
                            f"Invalid state transition: {existing_asset.status} -> {asset.status}"
                        )
                # 更新所有字段
                existing_asset.name = asset.name
                existing_asset.description = asset.description
                existing_asset.asset_type = asset.asset_type
                existing_asset.status = asset.status
                existing_asset.metadata = asset.metadata
                existing_asset.updated_at = datetime.utcnow()
                return self.asset_dao.update(existing_asset)
            else:
                # 使用AssetUpdateRequest更新
                # 验证状态转换
                if request.status and request.status != existing_asset.status:
                    if not request.status.can_transition_to(existing_asset.status):
                        raise ValueError(
                            f"Invalid state transition: {existing_asset.status} -> {request.status}"
                        )

                # 更新字段
                if request.name is not None:
                    existing_asset.name = request.name
                if request.description is not None:
                    existing_asset.description = request.description
                if request.asset_type is not None:
                    existing_asset.asset_type = request.asset_type
                if request.status is not None:
                    existing_asset.status = request.status
                if request.metadata is not None:
                    existing_asset.metadata = request.metadata

                existing_asset.updated_at = datetime.utcnow()

                # 保存更新
                return self.asset_dao.update(existing_asset)
        else:
            # 使用内存存储
            existing_asset = self._assets.get(asset_id)
            if not existing_asset:
                return None

            # 如果传入的是完整Asset对象
            if isinstance(asset_or_id, Asset):
                # 验证状态转换
                if asset.status != existing_asset.status:
                    if not asset.status.can_transition_to(existing_asset.status):
                        raise ValueError(
                            f"Invalid state transition: {existing_asset.status} -> {asset.status}"
                        )
                # 直接替换整个对象
                asset.updated_at = datetime.utcnow()
                self._assets[asset_id] = asset
                return asset
            else:
                # 使用AssetUpdateRequest更新
                # 验证状态转换
                if request.status and request.status != existing_asset.status:
                    if not request.status.can_transition_to(existing_asset.status):
                        raise ValueError(
                            f"Invalid state transition: {existing_asset.status} -> {request.status}"
                        )

                # 更新字段
                if request.name is not None:
                    existing_asset.name = request.name
                if request.description is not None:
                    existing_asset.description = request.description
                if request.asset_type is not None:
                    existing_asset.asset_type = request.asset_type
                if request.status is not None:
                    existing_asset.status = request.status
                if request.metadata is not None:
                    existing_asset.metadata = request.metadata

                existing_asset.updated_at = datetime.utcnow()

                return existing_asset

    def delete_asset(self, asset_id: str) -> bool:
        """
        删除资产（标记为退役）

        Args:
            asset_id: 资产ID

        Returns:
            是否删除成功
        """
        if self.asset_dao:
            # 使用数据库 - 先更新为退役状态
            asset = self.asset_dao.select_by_id(asset_id)
            if not asset:
                return False

            asset.status = AssetStatus.DECOMMISSIONED
            asset.updated_at = datetime.utcnow()
            self.asset_dao.update(asset)

            return True
        else:
            # 使用内存存储
            if asset_id not in self._assets:
                return False

            # 标记为退役
            self._assets[asset_id].status = AssetStatus.DECOMMISSIONED
            self._assets[asset_id].updated_at = datetime.utcnow()

            return True

    def list_assets(self, params: AssetQueryParams = None):
        """
        查询资产列表

        Args:
            params: 查询参数；如果不提供则直接返回资产列表

        Returns:
            资产列表或资产列表响应
        """
        if params is None:
            if self.asset_dao:
                return self.asset_dao.list()
            return list(self._assets.values())

        filters = {}
        if params.asset_type:
            filters["asset_type"] = params.asset_type
        if params.status:
            filters["status"] = params.status
        if params.search:
            filters["search"] = params.search

        if self.asset_dao:
            assets = self.asset_dao.list(
                filters=filters,
                limit=params.page_size,
                offset=(params.page - 1) * params.page_size,
                order_by=(f"-{params.sort_by}" if params.sort_order == "desc" else params.sort_by)
            )
            total = self.asset_dao.count(filters)
        else:
            assets = list(self._assets.values())
            total = len(assets)

        total_pages = math.ceil(total / params.page_size) if params.page_size else 0
        return AssetListResponse(
            assets=assets,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages
        )

    def get_asset_stats(self) -> AssetStats:
        """
        获取资产统计信息

        Returns:
            资产统计信息
        """
        if self.asset_dao:
            total = self.asset_dao.count({})
            type_stats = {asset_type.value: self.asset_dao.count({"asset_type": asset_type}) for asset_type in AssetType}
            status_stats = {status.value: self.asset_dao.count({"status": status}) for status in AssetStatus}
        else:
            assets = list(self._assets.values())
            total = len(assets)
            type_stats = {}
            status_stats = {}
            for asset in assets:
                type_stats[asset.asset_type.value] = type_stats.get(asset.asset_type.value, 0) + 1
                status_stats[asset.status.value] = status_stats.get(asset.status.value, 0) + 1

        active_nodes = status_stats.get(AssetStatus.ACTIVE.value, 0)
        inactive_nodes = status_stats.get(AssetStatus.INACTIVE.value, 0)
        return AssetStats(
            total_assets=total,
            by_type=type_stats,
            by_status=status_stats,
            active_nodes=active_nodes,
            inactive_nodes=inactive_nodes,
        )

    def get_statistics(self) -> Dict[str, Any]:
        """兼容旧测试的统计接口，返回字典"""
        stats = self.get_asset_stats()
        return {
            "total_assets": stats.total_assets,
            "by_type": stats.by_type,
            "by_status": stats.by_status,
            "active_nodes": stats.active_nodes,
            "inactive_nodes": stats.inactive_nodes,
        }

    def update_heartbeat(self, asset_id: str) -> bool:
        """
        更新资产心跳时间

        Args:
            asset_id: 资产ID

        Returns:
            是否更新成功
        """
        if self.asset_dao:
            asset = self.asset_dao.select_by_id(asset_id)
            if not asset:
                return False

            asset.last_heartbeat = datetime.utcnow()
            asset.status = AssetStatus.ACTIVE
            asset.updated_at = datetime.utcnow()

            self.asset_dao.update(asset)
            return True
        else:
            asset = self._assets.get(asset_id)
            if not asset:
                return False

            asset.last_heartbeat = datetime.utcnow()
            asset.status = AssetStatus.ACTIVE
            asset.updated_at = datetime.utcnow()

            return True

    def update_asset_heartbeat(self, asset_id: str) -> bool:
        """兼容API端点的心跳更新方法"""
        return self.update_heartbeat(asset_id)

    def associate_node(self, asset_id: str, node_id: str) -> bool:
        """
        关联运行节点到资产

        Args:
            asset_id: 资产ID
            node_id: 节点ID

        Returns:
            是否关联成功
        """
        if self.asset_dao:
            asset = self.asset_dao.select_by_id(asset_id)
            if not asset:
                return False

            asset.associated_node_id = node_id
            asset.status = AssetStatus.ACTIVE
            asset.updated_at = datetime.utcnow()

            self.asset_dao.update(asset)
            return True
        else:
            asset = self._assets.get(asset_id)
            if not asset:
                return False

            asset.associated_node_id = node_id
            asset.status = AssetStatus.ACTIVE
            asset.updated_at = datetime.utcnow()

            return True

    def disassociate_node(self, asset_id: str) -> bool:
        """
        取消资产与运行节点的关联

        Args:
            asset_id: 资产ID

        Returns:
            是否取消关联成功
        """
        if self.asset_dao:
            asset = self.asset_dao.select_by_id(asset_id)
            if not asset:
                return False

            asset.associated_node_id = None
            asset.status = AssetStatus.INACTIVE
            asset.updated_at = datetime.utcnow()

            self.asset_dao.update(asset)
            return True
        else:
            asset = self._assets.get(asset_id)
            if not asset:
                return False

            asset.associated_node_id = None
            asset.status = AssetStatus.INACTIVE
            asset.updated_at = datetime.utcnow()

            return True

    def get_assets_by_node(self, node_id: str) -> List[Asset]:
        """
        获取节点上的资产列表

        Args:
            node_id: 节点ID

        Returns:
            资产列表
        """
        if self.asset_dao:
            all_assets = self.asset_dao.list({})
            return [a for a in all_assets if getattr(a.metadata, "custom_properties", {}).get("node_id") == node_id]
        else:
            return [a for a in self._assets.values() if getattr(a.metadata, "custom_properties", {}).get("node_id") == node_id]

    def _audit_asset_event(self, asset: Asset, action: AuditAction, message: str) -> None:
        if not self.database:
            return
        from shared.services.audit_service import AuditService
        audit_service = AuditService(database=self.database)
        audit_service.log_action(
            AuditLogCreateRequest(
                action=action,
                category=AuditCategory.ASSET,
                level=EventLevel.INFO,
                actor="system",
                target_type="asset",
                target_id=asset.asset_id,
                related_asset_id=asset.asset_id,
                message=message,
                details={
                    "asset_name": asset.name,
                    "asset_type": asset.asset_type.value,
                    "status": asset.status.value,
                },
            )
        )


# 全局服务实例（用于简单的单例模式）
_asset_service_instance = None


def get_asset_service(database=None):
    """
    获取资产服务实例（单例模式）

    Args:
        database: 数据库实例（首次调用时提供）

    Returns:
        AssetService 实例
    """
    global _asset_service_instance
    if _asset_service_instance is None:
        _asset_service_instance = AssetService(database=database)
    elif database is not None and _asset_service_instance.database is None:
        # 如果首次创建时没有数据库，但后续提供了数据库，则重新创建
        _asset_service_instance = AssetService(database=database)
    return _asset_service_instance
