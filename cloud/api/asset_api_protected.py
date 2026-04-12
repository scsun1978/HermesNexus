"""
HermesNexus Phase 2 - Protected Asset API Example
带认证保护的资产管理API示例
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional

from shared.models.asset import (
    Asset,
    AssetCreateRequest,
    AssetUpdateRequest,
    AssetQueryParams,
    AssetListResponse,
)
from shared.services.asset_service import AssetService
from shared.security.middleware import require_auth, AuthMiddleware
from shared.security.permissions import Permission

# 创建路由器
router = APIRouter(prefix="/api/v1/assets", tags=["Assets"])

# 初始化服务（应该从main.py传入）
asset_service = AssetService(database=None)


# GET /api/v1/assets - 获取资产列表（需要认证）
@router.get("", response_model=AssetListResponse)
async def list_assets(
    page: int = 1,
    page_size: int = 20,
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_user: dict = Depends(require_auth),  # 🔒 需要认证
):
    """
    获取资产列表

    权限要求：asset:read
    """
    params = AssetQueryParams(
        page=page,
        page_size=page_size,
        asset_type=asset_type,
        status=status,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return asset_service.list_assets(params)


# POST /api/v1/assets - 创建资产（需要认证和写权限）
@router.post("", response_model=Asset, status_code=status.HTTP_201_CREATED)
async def create_asset(
    request: AssetCreateRequest,
    current_user: dict = Depends(
        AuthMiddleware.require_permission(Permission.ASSET_WRITE)
    ),  # 🔒 需要写权限
):
    """
    创建资产

    权限要求：asset:write
    """
    try:
        return asset_service.create_asset(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# GET /api/v1/assets/{asset_id} - 获取资产详情（需要认证）
@router.get("/{asset_id}", response_model=Asset)
async def get_asset(
    asset_id: str, current_user: dict = Depends(require_auth)  # 🔒 需要认证
):
    """
    获取资产详情

    权限要求：asset:read
    """
    asset = asset_service.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


# PUT /api/v1/assets/{asset_id} - 更新资产（需要认证和写权限）
@router.put("/{asset_id}", response_model=Asset)
async def update_asset(
    asset_id: str,
    request: AssetUpdateRequest,
    current_user: dict = Depends(
        AuthMiddleware.require_permission(Permission.ASSET_WRITE)
    ),  # 🔒 需要写权限
):
    """
    更新资产

    权限要求：asset:write
    """
    try:
        asset = asset_service.update_asset(asset_id, request)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        return asset
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# DELETE /api/v1/assets/{asset_id} - 删除资产（需要认证和删除权限）
@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    current_user: dict = Depends(
        AuthMiddleware.require_permission(Permission.ASSET_DELETE)
    ),  # 🔒 需要删除权限
):
    """
    删除资产（标记为退役）

    权限要求：asset:delete
    """
    success = asset_service.delete_asset(asset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"deleted": True}


# POST /api/v1/assets/{asset_id}/heartbeat - 更新心跳（需要认证）
@router.post("/{asset_id}/heartbeat")
async def update_heartbeat(
    asset_id: str, current_user: dict = Depends(require_auth)  # 🔒 需要认证
):
    """
    更新资产心跳

    权限要求：asset:write
    """
    success = asset_service.update_heartbeat(asset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"updated": True}


# GET /api/v1/assets/stats - 获取资产统计（需要认证）
@router.get("/stats")
async def get_asset_stats(current_user: dict = Depends(require_auth)):  # 🔒 需要认证
    """
    获取资产统计信息

    权限要求：asset:read
    """
    return asset_service.get_asset_stats()


# 使用示例：
# 1. 使用Bearer Token认证：
#    curl -H "Authorization: Bearer dev-token-12345" http://localhost:8080/api/v1/assets
#
# 2. 使用API Key认证：
#    curl -H "X-API-Key: sk-xxxxx" http://localhost:8080/api/v1/assets
#
# 3. 开发环境关闭认证（AUTH_ENABLED=false）：
#    curl http://localhost:8080/api/v1/assets
