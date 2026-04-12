"""
HermesNexus Phase 2 - Asset Service
资产管理业务逻辑层
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from shared.models.asset import (
    Asset,
    AssetCreateRequest,
    AssetUpdateRequest,
    AssetQueryParams,
    AssetListResponse,
    AssetStats,
    AssetType,
    AssetStatus,
)


class AssetService:
    """资产管理服务"""

    def __init__(self, database=None):
        """
        初始化资产服务

        Args:
            database: 数据库实例（可以是 SQLAlchemy, SQLite 等）
        """
        self.database = database
        self._assets: Dict[str, Asset] = {}  # 内存存储（Phase 2 MVP）

    def create_asset(self, request: AssetCreateRequest) -> Asset:
        """
        创建资产

        Args:
            request: 资产创建请求

        Returns:
            创建的资产

        Raises:
            ValueError: 如果资产ID已存在
        """
        # 生成或使用提供的资产ID
        asset_id = request.asset_id or f"asset-{uuid.uuid4().hex[:8]}"

        # 检查ID是否已存在
        if asset_id in self._assets:
            raise ValueError(f"Asset with ID '{asset_id}' already exists")

        # 创建资产对象
        asset = Asset(
            asset_id=asset_id,
            name=request.name,
            asset_type=request.asset_type,
            status=AssetStatus.REGISTERED,
            metadata=request.metadata or {},
            description=request.description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 保存资产
        self._assets[asset_id] = asset

        return asset

    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """
        获取资产详情

        Args:
            asset_id: 资产ID

        Returns:
            资产对象，如果不存在则返回 None
        """
        return self._assets.get(asset_id)

    def update_asset(
        self, asset_id: str, request: AssetUpdateRequest
    ) -> Optional[Asset]:
        """
        更新资产

        Args:
            asset_id: 资产ID
            request: 更新请求

        Returns:
            更新后的资产，如果不存在则返回 None

        Raises:
            ValueError: 如果状态转换不合法
        """
        asset = self._assets.get(asset_id)
        if not asset:
            return None

        # 更新字段
        if request.name is not None:
            asset.name = request.name
        if request.description is not None:
            asset.description = request.description
        if request.metadata is not None:
            asset.metadata = request.metadata

        # 状态转换验证
        if request.status is not None:
            if not asset.status.can_transition_to(request.status):
                raise ValueError(
                    f"Invalid status transition: {asset.status} -> {request.status}"
                )
            asset.status = request.status

        asset.updated_at = datetime.utcnow()

        return asset

    def delete_asset(self, asset_id: str) -> bool:
        """
        删除资产（标记为退役）

        Args:
            asset_id: 资产ID

        Returns:
            是否成功删除
        """
        asset = self._assets.get(asset_id)
        if not asset:
            return False

        # 检查是否可以退役
        if asset.status == AssetStatus.ACTIVE:
            raise ValueError("Cannot delete active asset. Deactivate it first.")

        # 标记为退役
        asset.status = AssetStatus.DECOMMISSIONED
        asset.updated_at = datetime.utcnow()

        return True

    def list_assets(self, params: AssetQueryParams) -> AssetListResponse:
        """
        列出资产

        Args:
            params: 查询参数

        Returns:
            资产列表响应
        """
        # 获取所有资产
        assets = list(self._assets.values())

        # 应用过滤
        if params.asset_type:
            assets = [a for a in assets if a.asset_type == params.asset_type]

        if params.status:
            assets = [a for a in assets if a.status == params.status]

        if params.search:
            search_lower = params.search.lower()
            assets = [
                a
                for a in assets
                if search_lower in a.name.lower()
                or (a.description and search_lower in a.description.lower())
                or (a.metadata.ip_address and search_lower in a.metadata.ip_address)
                or (a.metadata.hostname and search_lower in a.metadata.hostname.lower())
            ]

        if params.tags:
            assets = [
                a for a in assets if any(tag in a.metadata.tags for tag in params.tags)
            ]

        if params.groups:
            assets = [
                a
                for a in assets
                if any(group in a.metadata.groups for group in params.groups)
            ]

        # 排序
        reverse = params.sort_order == "desc"
        if hasattr(Asset, params.sort_by):
            assets.sort(key=lambda a: getattr(a, params.sort_by), reverse=reverse)

        # 分页
        total = len(assets)
        start = (params.page - 1) * params.page_size
        end = start + params.page_size
        paged_assets = assets[start:end]

        total_pages = (total + params.page_size - 1) // params.page_size

        return AssetListResponse(
            total=total,
            assets=paged_assets,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    def get_asset_stats(self) -> AssetStats:
        """
        获取资产统计信息

        Returns:
            资产统计信息
        """
        assets = list(self._assets.values())

        # 按类型统计
        by_type: Dict[str, int] = {}
        for asset_type in AssetType:
            count = sum(1 for a in assets if a.asset_type == asset_type)
            by_type[asset_type.value] = count

        # 按状态统计
        by_status: Dict[str, int] = {}
        for status in AssetStatus:
            count = sum(1 for a in assets if a.status == status)
            by_status[status.value] = count

        # 活跃/非活跃统计
        active_nodes = sum(1 for a in assets if a.status == AssetStatus.ACTIVE)
        inactive_nodes = sum(1 for a in assets if a.status == AssetStatus.INACTIVE)

        return AssetStats(
            total_assets=len(assets),
            by_type=by_type,
            by_status=by_status,
            active_nodes=active_nodes,
            inactive_nodes=inactive_nodes,
        )

    def update_asset_heartbeat(self, asset_id: str) -> bool:
        """
        更新资产心跳时间

        Args:
            asset_id: 资产ID

        Returns:
            是否成功更新
        """
        asset = self._assets.get(asset_id)
        if not asset:
            return False

        asset.last_heartbeat = datetime.utcnow()

        # 如果资产是 REGISTERED 或 INACTIVE 状态，更新为 ACTIVE
        if asset.status in [AssetStatus.REGISTERED, AssetStatus.INACTIVE]:
            asset.status = AssetStatus.ACTIVE

        asset.updated_at = datetime.utcnow()

        return True

    def associate_node(self, asset_id: str, node_id: str) -> bool:
        """
        关联运行节点

        Args:
            asset_id: 资产ID
            node_id: 节点ID

        Returns:
            是否成功关联
        """
        asset = self._assets.get(asset_id)
        if not asset:
            return False

        asset.associated_node_id = node_id
        asset.updated_at = datetime.utcnow()

        return True

    def disassociate_node(self, asset_id: str) -> bool:
        """
        取消关联运行节点

        Args:
            asset_id: 资产ID

        Returns:
            是否成功取消关联
        """
        asset = self._assets.get(asset_id)
        if not asset:
            return False

        asset.associated_node_id = None
        asset.updated_at = datetime.utcnow()

        return True


# 全局服务实例（Phase 2 MVP 使用内存存储）
_asset_service: Optional[AssetService] = None


def get_asset_service() -> AssetService:
    """获取全局资产服务实例"""
    global _asset_service
    if _asset_service is None:
        _asset_service = AssetService()
    return _asset_service
