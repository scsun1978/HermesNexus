"""
HermesNexus Phase 2 - Asset API Endpoints
资产管理 API 端点
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime

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
from shared.services.asset_service import get_asset_service
from shared.models.enums import ErrorCode, create_error_response

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.post(
    "",
    response_model=Asset,
    status_code=status.HTTP_201_CREATED,
    summary="创建资产",
    description="注册新的资产到系统中",
)
async def create_asset(request: AssetCreateRequest):
    """
    创建资产

    - **name**: 资产名称（必需）
    - **asset_type**: 资产类型（必需）
    - **description**: 资产描述（可选）
    - **metadata**: 资产元数据（可选）
    """
    try:
        service = get_asset_service()
        asset = service.create_asset(request)
        return asset
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=create_error_response(
                ErrorCode.ASSET_ALREADY_EXISTS, details={"error": str(e)}
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.get(
    "",
    response_model=AssetListResponse,
    summary="列出资产",
    description="获取资产列表，支持分页、搜索和过滤",
)
async def list_assets(
    asset_type: Optional[AssetType] = Query(None, description="按资产类型过滤"),
    status: Optional[AssetStatus] = Query(None, description="按状态过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    tags: Optional[List[str]] = Query(None, description="按标签过滤"),
    groups: Optional[List[str]] = Query(None, description="按分组过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
):
    """
    列出资产

    支持的查询参数：
    - **asset_type**: 按资产类型过滤
    - **status**: 按状态过滤
    - **search**: 搜索关键词（名称、描述、IP地址）
    - **tags**: 按标签过滤
    - **groups**: 按分组过滤
    - **page**: 页码（从1开始）
    - **page_size**: 每页大小（1-100）
    - **sort_by**: 排序字段
    - **sort_order**: 排序方向（asc/desc）
    """
    try:
        service = get_asset_service()

        params = AssetQueryParams(
            asset_type=asset_type,
            status=status,
            search=search,
            tags=tags or [],
            groups=groups or [],
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return service.list_assets(params)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.get(
    "/stats",
    response_model=AssetStats,
    summary="获取资产统计",
    description="获取资产统计信息，包括按类型和状态的分布",
)
async def get_asset_stats():
    """
    获取资产统计信息

    返回：
    - 总资产数
    - 按类型统计
    - 按状态统计
    - 活跃/非活跃节点数
    """
    try:
        service = get_asset_service()
        return service.get_asset_stats()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.get(
    "/{asset_id}",
    response_model=Asset,
    summary="获取资产详情",
    description="根据资产ID获取资产详细信息",
)
async def get_asset(asset_id: str):
    """
    获取资产详情

    - **asset_id**: 资产唯一标识
    """
    try:
        service = get_asset_service()
        asset = service.get_asset(asset_id)

        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_error_response(
                    ErrorCode.ASSET_NOT_FOUND, details={"asset_id": asset_id}
                ),
            )

        return asset
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.put(
    "/{asset_id}", response_model=Asset, summary="更新资产", description="更新资产信息"
)
async def update_asset(asset_id: str, request: AssetUpdateRequest):
    """
    更新资产

    - **asset_id**: 资产唯一标识
    - **name**: 新的资产名称（可选）
    - **description**: 新的资产描述（可选）
    - **status**: 新的资产状态（可选）
    - **metadata**: 新的资产元数据（可选）
    """
    try:
        service = get_asset_service()

        # 检查资产是否存在
        existing_asset = service.get_asset(asset_id)
        if not existing_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_error_response(
                    ErrorCode.ASSET_NOT_FOUND, details={"asset_id": asset_id}
                ),
            )

        # 更新资产
        updated_asset = service.update_asset(asset_id, request)
        return updated_asset

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_error_response(
                ErrorCode.ASSET_INVALID_STATE_TRANSITION, details={"error": str(e)}
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除资产",
    description="删除资产（标记为退役状态）",
)
async def delete_asset(asset_id: str):
    """
    删除资产

    注意：此操作会将资产标记为退役状态，而不是真正删除数据。

    - **asset_id**: 资产唯一标识
    """
    try:
        service = get_asset_service()

        # 检查资产是否存在
        existing_asset = service.get_asset(asset_id)
        if not existing_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_error_response(
                    ErrorCode.ASSET_NOT_FOUND, details={"asset_id": asset_id}
                ),
            )

        # 删除资产
        success = service.delete_asset(asset_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=create_error_response(
                    ErrorCode.ASSET_INVALID_STATE_TRANSITION,
                    details={"message": "Cannot delete asset in current state"},
                ),
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.post(
    "/{asset_id}/heartbeat",
    status_code=status.HTTP_200_OK,
    summary="资产心跳",
    description="更新资产最后心跳时间",
)
async def asset_heartbeat(asset_id: str):
    """
    资产心跳

    由边缘节点定期调用以保持资产状态为活跃。

    - **asset_id**: 资产唯一标识
    """
    try:
        service = get_asset_service()

        # 检查资产是否存在
        existing_asset = service.get_asset(asset_id)
        if not existing_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_error_response(
                    ErrorCode.ASSET_NOT_FOUND, details={"asset_id": asset_id}
                ),
            )

        # 更新心跳
        success = service.update_asset_heartbeat(asset_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=create_error_response(
                    ErrorCode.INT_INTERNAL_SERVICE_ERROR,
                    details={"message": "Failed to update heartbeat"},
                ),
            )

        return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.post(
    "/{asset_id}/nodes/{node_id}",
    status_code=status.HTTP_200_OK,
    summary="关联节点",
    description="将运行节点关联到资产",
)
async def associate_node(asset_id: str, node_id: str):
    """
    关联运行节点

    - **asset_id**: 资产唯一标识
    - **node_id**: 节点唯一标识
    """
    try:
        service = get_asset_service()

        # 检查资产是否存在
        existing_asset = service.get_asset(asset_id)
        if not existing_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_error_response(
                    ErrorCode.ASSET_NOT_FOUND, details={"asset_id": asset_id}
                ),
            )

        # 关联节点
        success = service.associate_node(asset_id, node_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=create_error_response(
                    ErrorCode.INT_INTERNAL_SERVICE_ERROR,
                    details={"message": "Failed to associate node"},
                ),
            )

        return {"status": "ok", "node_id": node_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.delete(
    "/{asset_id}/nodes",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="取消关联节点",
    description="取消资产与运行节点的关联",
)
async def disassociate_node(asset_id: str):
    """
    取消关联节点

    - **asset_id**: 资产唯一标识
    """
    try:
        service = get_asset_service()

        # 检查资产是否存在
        existing_asset = service.get_asset(asset_id)
        if not existing_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_error_response(
                    ErrorCode.ASSET_NOT_FOUND, details={"asset_id": asset_id}
                ),
            )

        # 取消关联
        success = service.disassociate_node(asset_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=create_error_response(
                    ErrorCode.INT_INTERNAL_SERVICE_ERROR,
                    details={"message": "Failed to disassociate node"},
                ),
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )
