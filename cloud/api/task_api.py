"""
HermesNexus Phase 2 - Task API Endpoints
任务编排 API 端点
"""

from fastapi import APIRouter, HTTPException, Query, status, Header
from typing import List, Optional

from shared.models.task import (
    Task,
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskQueryParams,
    TaskListResponse,
    TaskStats,
    TaskDispatchRequest,
    TaskResultSubmit,
    TaskType,
    TaskStatus,
    TaskPriority,
)
from shared.services.task_service import get_task_service
from shared.models.enums import ErrorCode, create_error_response

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def get_current_user(authorization: Optional[str] = None) -> str:
    """获取当前用户（安全增强版）"""
    # 安全检查：确保Authorization header存在
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )

    # 简化实现：从Bearer token中提取用户名
    # 实际生产环境应该验证JWT token签名和过期时间
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Expected: Bearer <token>"
        )

    # Phase 2 MVP: 简化实现，从token中提取用户信息
    # 格式假设: "Bearer <username>" 或实际JWT token
    token = authorization[7:].strip()  # 移除 "Bearer " 前缀

    # 如果是简单的用户名token（MVP阶段）
    if token and not token.count('.') == 2:  # 不是JWT格式
        return token

    # Phase 2 Full: 解析JWT token获取用户信息
    # 这里应该验证JWT签名、过期时间等
    # 暂时返回admin作为fallback，但记录警告
    import logging
    logging.warning(f"JWT token validation not implemented, using fallback for token: {token[:10]}...")
    return "admin"


@router.post(
    "",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    summary="创建任务",
    description="创建新的任务并添加到调度队列",
)
async def create_task(request: TaskCreateRequest, authorization: Optional[str] = Header(None)):
    """
    创建任务

    - **name**: 任务名称（必需）
    - **task_type**: 任务类型（必需）
    - **priority**: 任务优先级
    - **target_asset_id**: 目标资产ID（必需）
    - **command**: 要执行的命令（必需）
    - **timeout**: 超时时间（秒）
    - **scheduled_at**: 计划执行时间（可选）
    """
    try:
        service = get_task_service()
        created_by = get_current_user(authorization)
        task = service.create_task(request, created_by)
        return task
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=create_error_response(ErrorCode.VALIDATION_ERROR, details={"error": str(e)}),
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
    response_model=TaskListResponse,
    summary="列出任务",
    description="获取任务列表，支持分页、搜索和过滤",
)
async def list_tasks(
    task_type: Optional[TaskType] = Query(None, description="按任务类型过滤"),
    status: Optional[TaskStatus] = Query(None, description="按状态过滤"),
    priority: Optional[TaskPriority] = Query(None, description="按优先级过滤"),
    target_asset_id: Optional[str] = Query(None, description="按目标资产过滤"),
    target_node_id: Optional[str] = Query(None, description="按目标节点过滤"),
    created_by: Optional[str] = Query(None, description="按创建者过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    tags: Optional[List[str]] = Query(None, description="按标签过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
):
    """
    列出任务

    支持的查询参数：
    - **task_type**: 按任务类型过滤
    - **status**: 按状态过滤
    - **priority**: 按优先级过滤
    - **target_asset_id**: 按目标资产过滤
    - **target_node_id**: 按目标节点过滤
    - **created_by**: 按创建者过滤
    - **search**: 搜索关键词
    - **tags**: 按标签过滤
    - **page**: 页码（从1开始）
    - **page_size**: 每页大小（1-100）
    - **sort_by**: 排序字段
    - **sort_order**: 排序方向（asc/desc）
    """
    try:
        service = get_task_service()

        params = TaskQueryParams(
            task_type=task_type,
            status=status,
            priority=priority,
            target_asset_id=target_asset_id,
            target_node_id=target_node_id,
            created_by=created_by,
            search=search,
            tags=tags or [],
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return service.list_tasks(params)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.get(
    "/stats",
    response_model=TaskStats,
    summary="获取任务统计",
    description="获取任务统计信息，包括按类型、状态、优先级的分布",
)
async def get_task_stats():
    """
    获取任务统计信息

    返回：
    - 总任务数
    - 按类型统计
    - 按状态统计
    - 按优先级统计
    - 执行统计（运行中、待处理、已完成、失败）
    - 成功率
    """
    try:
        service = get_task_service()
        return service.get_task_stats()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.get(
    "/{task_id}",
    response_model=Task,
    summary="获取任务详情",
    description="根据任务ID获取任务详细信息",
)
async def get_task(task_id: str):
    """
    获取任务详情

    - **task_id**: 任务唯一标识
    """
    try:
        service = get_task_service()
        task = service.get_task(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_error_response(
                    ErrorCode.TASK_NOT_FOUND, details={"task_id": task_id}
                ),
            )

        return task
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
    "/{task_id}",
    response_model=Task,
    summary="更新任务",
    description="更新任务信息（仅限非运行中的任务）",
)
async def update_task(task_id: str, request: TaskUpdateRequest):
    """
    更新任务

    注意：运行中的任务不能修改，只能取消。

    - **task_id**: 任务唯一标识
    - **name**: 新的任务名称（可选）
    - **priority**: 新的任务优先级（可选）
    - **status**: 新的任务状态（可选）
    - **description**: 新的任务描述（可选）
    - **tags**: 新的任务标签（可选）
    """
    try:
        service = get_task_service()

        # 检查任务是否存在
        existing_task = service.get_task(task_id)
        if not existing_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_error_response(
                    ErrorCode.TASK_NOT_FOUND, details={"task_id": task_id}
                ),
            )

        # 更新任务
        updated_task = service.update_task(task_id, request)
        return updated_task

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_error_response(
                ErrorCode.TASK_INVALID_STATE_TRANSITION, details={"error": str(e)}
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.post(
    "/{task_id}/cancel",
    response_model=Task,
    summary="取消任务",
    description="取消任务执行",
)
async def cancel_task(task_id: str):
    """
    取消任务

    注意：已完成的任务不能取消。

    - **task_id**: 任务唯一标识
    """
    try:
        service = get_task_service()

        # 检查任务是否存在
        existing_task = service.get_task(task_id)
        if not existing_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_error_response(
                    ErrorCode.TASK_NOT_FOUND, details={"task_id": task_id}
                ),
            )

        # 取消任务
        cancelled_task = service.cancel_task(task_id)
        return cancelled_task

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_error_response(ErrorCode.TASK_CANCELLED, details={"error": str(e)}),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.post(
    "/dispatch",
    response_model=List[Task],
    summary="分发任务",
    description="批量分发任务到指定节点",
)
async def dispatch_tasks(request: TaskDispatchRequest):
    """
    分发任务

    将待调度的任务分配给指定的执行节点。

    - **task_ids**: 要分发的任务ID列表
    - **target_node_id**: 目标节点ID
    - **dispatch_strategy**: 分发策略
    """
    try:
        service = get_task_service()
        dispatched_tasks = service.dispatch_tasks(request)
        return dispatched_tasks
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_error_response(ErrorCode.TASK_INVALID_TARGET, details={"error": str(e)}),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )


@router.post(
    "/{task_id}/result",
    status_code=status.HTTP_200_OK,
    summary="提交任务结果",
    description="边缘节点提交任务执行结果",
)
async def submit_task_result(task_id: str, submission: TaskResultSubmit):
    """
    提交任务结果

    由边缘节点在任务执行完成后调用。

    - **task_id**: 任务唯一标识
    - **submission**: 执行结果
    """
    try:
        service = get_task_service()

        # 设置任务ID
        submission.task_id = task_id

        # 提交结果
        updated_task = service.submit_task_result(submission)

        if not updated_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_error_response(
                    ErrorCode.TASK_NOT_FOUND, details={"task_id": task_id}
                ),
            )

        return updated_task

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_error_response(
                ErrorCode.TASK_EXECUTION_FAILED, details={"error": str(e)}
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
    "/nodes/{node_id}/pending",
    response_model=List[Task],
    summary="获取节点待执行任务",
    description="边缘节点获取分配给自己的待执行任务列表",
)
async def get_pending_tasks_for_node(
    node_id: str, limit: int = Query(10, ge=1, le=100, description="最大返回数量")
):
    """
    获取节点待执行任务

    由边缘节点定期轮询，获取分配给自己的待执行任务。

    - **node_id**: 节点唯一标识
    - **limit**: 最大返回数量
    """
    try:
        service = get_task_service()
        pending_tasks = service.get_pending_tasks_for_node(node_id, limit)
        return pending_tasks
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                ErrorCode.INT_INTERNAL_SERVICE_ERROR, details={"error": str(e)}
            ),
        )
