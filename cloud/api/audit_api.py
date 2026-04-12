"""
HermesNexus Phase 2 - Audit API Endpoints
审计日志 API 端点
"""

from fastapi import APIRouter, HTTPException, Query, status, Header
from typing import List, Optional
from datetime import datetime

from shared.models.audit import (
    AuditLog,
    AuditLogCreateRequest,
    AuditLogQueryParams,
    AuditLogListResponse,
    AuditStats,
    AuditExportRequest,
    AuditAction,
    AuditCategory,
    EventLevel,
)
from shared.services.audit_service import get_audit_service
from shared.models.enums import ErrorCode, create_error_response

router = APIRouter(prefix="/api/v1/audit_logs", tags=["audit_logs"])


def get_current_user(authorization: Optional[str] = None) -> str:
    """获取当前用户（简化实现）"""
    return "admin"


def get_client_info(request) -> tuple:
    """获取客户端信息"""
    # 获取真实IP（考虑代理）
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else "unknown"

    # 获取用户代理
    user_agent = request.headers.get("User-Agent", "unknown")

    return ip_address, user_agent


@router.post(
    "",
    response_model=AuditLog,
    status_code=status.HTTP_201_CREATED,
    summary="记录审计日志",
    description="记录新的审计日志事件",
)
async def create_audit_log(
    request: AuditLogCreateRequest, authorization: Optional[str] = Header(None)
):
    """
    记录审计日志

    - **action**: 审计动作类型（必需）
    - **category**: 审计分类（必需）
    - **level**: 事件级别
    - **actor**: 操作发起者（必需）
    - **target_type**: 目标对象类型（必需）
    - **target_id**: 目标对象ID
    - **message**: 事件描述消息（必需）
    - **details**: 事件详细信息
    """
    try:
        service = get_audit_service()
        audit_log = service.log_action(request)
        return audit_log
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.get(
    "",
    response_model=AuditLogListResponse,
    summary="查询审计日志",
    description="获取审计日志列表，支持分页、搜索和过滤",
)
async def query_audit_logs(
    action: Optional[AuditAction] = Query(None, description="按动作类型过滤"),
    category: Optional[AuditCategory] = Query(None, description="按分类过滤"),
    level: Optional[EventLevel] = Query(None, description="按级别过滤"),
    actor: Optional[str] = Query(None, description="按操作者过滤"),
    target_type: Optional[str] = Query(None, description="按目标类型过滤"),
    target_id: Optional[str] = Query(None, description="按目标ID过滤"),
    related_task_id: Optional[str] = Query(None, description="按关联任务过滤"),
    related_node_id: Optional[str] = Query(None, description="按关联节点过滤"),
    related_asset_id: Optional[str] = Query(None, description="按关联资产过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=500, description="每页大小"),
    sort_by: str = Query("timestamp", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
):
    """
    查询审计日志

    支持的查询参数：
    - **action**: 按动作类型过滤
    - **category**: 按分类过滤
    - **level**: 按级别过滤
    - **actor**: 按操作者过滤
    - **target_type**: 按目标类型过滤
    - **target_id**: 按目标ID过滤
    - **related_task_id**: 按关联任务过滤
    - **related_node_id**: 按关联节点过滤
    - **related_asset_id**: 按关联资产过滤
    - **search**: 搜索关键词
    - **start_time**: 开始时间
    - **end_time**: 结束时间
    - **page**: 页码（从1开始）
    - **page_size**: 每页大小（1-500）
    - **sort_by**: 排序字段
    - **sort_order**: 排序方向（asc/desc）
    """
    try:
        service = get_audit_service()

        params = AuditLogQueryParams(
            action=action,
            category=category,
            level=level,
            actor=actor,
            target_type=target_type,
            target_id=target_id,
            related_task_id=related_task_id,
            related_node_id=related_node_id,
            related_asset_id=related_asset_id,
            search=search,
            start_time=start_time,
            end_time=end_time,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return service.query_logs(params)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.get(
    "/stats",
    response_model=AuditStats,
    summary="获取审计统计",
    description="获取审计日志统计信息",
)
async def get_audit_stats():
    """
    获取审计统计信息

    返回：
    - 总事件数
    - 按分类统计
    - 按动作统计
    - 按级别统计
    - 时间范围统计
    - 错误统计
    """
    try:
        service = get_audit_service()
        return service.get_audit_stats()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.get(
    "/tasks/{task_id}",
    response_model=List[AuditLog],
    summary="获取任务审计日志",
    description="获取特定任务的所有审计日志",
)
async def get_task_audit_logs(
    task_id: str, limit: int = Query(100, ge=1, le=1000, description="最大返回数量")
):
    """
    获取任务审计日志

    返回与指定任务相关的所有审计日志，按时间倒序排列。

    - **task_id**: 任务唯一标识
    - **limit**: 最大返回数量
    """
    try:
        service = get_audit_service()
        logs = service.get_logs_by_task(task_id, limit)
        return logs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.get(
    "/nodes/{node_id}",
    response_model=List[AuditLog],
    summary="获取节点审计日志",
    description="获取特定节点的所有审计日志",
)
async def get_node_audit_logs(
    node_id: str, limit: int = Query(100, ge=1, le=1000, description="最大返回数量")
):
    """
    获取节点审计日志

    返回与指定节点相关的所有审计日志，按时间倒序排列。

    - **node_id**: 节点唯一标识
    - **limit**: 最大返回数量
    """
    try:
        service = get_audit_service()
        logs = service.get_logs_by_node(node_id, limit)
        return logs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.get(
    "/assets/{asset_id}",
    response_model=List[AuditLog],
    summary="获取资产审计日志",
    description="获取特定资产的所有审计日志",
)
async def get_asset_audit_logs(
    asset_id: str, limit: int = Query(100, ge=1, le=1000, description="最大返回数量")
):
    """
    获取资产审计日志

    返回与指定资产相关的所有审计日志，按时间倒序排列。

    - **asset_id**: 资产唯一标识
    - **limit**: 最大返回数量
    """
    try:
        service = get_audit_service()
        logs = service.get_logs_by_asset(asset_id, limit)
        return logs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.post(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="导出审计日志",
    description="导出审计日志为 JSON 或 CSV 格式",
)
async def export_audit_logs(request: AuditExportRequest):
    """
    导出审计日志

    支持导出为 JSON 或 CSV 格式，可以指定时间范围、分类、级别等过滤条件。

    - **start_time**: 开始时间
    - **end_time**: 结束时间
    - **category**: 审计分类
    - **level**: 事件级别
    - **format**: 导出格式（json, csv）
    - **limit**: 最大导出数量
    """
    try:
        service = get_audit_service()

        # 设置默认时间范围（如果未指定）
        if not request.start_time and not request.end_time:
            from datetime import timedelta

            request.end_time = datetime.utcnow()
            request.start_time = request.end_time - timedelta(days=7)

        content = service.export_logs(request)

        # 返回文件响应
        from fastapi.responses import Response

        media_type = "application/json" if request.format == "json" else "text/csv"
        filename = (
            f"audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{request.format}"
        )

        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_error_response(
                ErrorCode.VALIDATION_ERROR, details={"error": str(e)}
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )
