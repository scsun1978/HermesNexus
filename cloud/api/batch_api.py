"""
批量任务调度 API - Week 5-6
支持批量创建和查询云边任务编排
"""
from fastapi import APIRouter, HTTPException, Query, status, Header
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from hermesnexus.orchestrator.cloud import (
    CloudTaskOrchestrator,
    MVPOrchestratorFactory,
    BatchScheduleResult
)
from hermesnexus.task.manager import TaskManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/tasks/batch", tags=["batch-tasks"])


# ==================== 全局编排器实例 ====================

_orchestrator_instance = None

def get_orchestrator() -> CloudTaskOrchestrator:
    """获取共享编排器实例（单例模式）"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        # 使用共享数据库
        db_path = "data/tasks.db"
        import os
        os.makedirs("data", exist_ok=True)

        task_manager = TaskManager(db_path)
        _orchestrator_instance = MVPOrchestratorFactory.create_with_default_config(task_manager)

        logger.info("Initialized shared CloudTaskOrchestrator with MVP factory")

    return _orchestrator_instance


# ==================== 数据模型 ====================

class BatchTaskRequest(BaseModel):
    """批量任务创建请求"""
    name: str
    command: str
    description: Optional[str] = None
    created_by: Optional[str] = "system"

    # 目标设备
    device_ids: Optional[List[str]] = None  # 直接指定设备列表
    group_id: Optional[str] = None  # 或使用设备分组

    # 调度选项
    parallel: bool = True  # 是否并行调度
    priority: str = "medium"  # 任务优先级

    class Config:
        json_schema_extra = {
            "example": {
                "name": "系统巡检",
                "command": "uptime && df -h",
                "description": "系统健康检查",
                "device_ids": ["server-001", "server-002", "server-003"],
                "parallel": True,
                "priority": "high"
            }
        }


class BatchTaskResponse(BaseModel):
    """批量任务响应"""
    batch_id: str
    name: str
    command: str
    total_devices: int
    successful_schedules: int
    failed_schedules: int
    task_ids: List[str]
    errors: Dict[str, str]
    progress_percentage: float
    status: str
    created_at: str


class DeviceGroupRequest(BaseModel):
    """设备分组创建请求"""
    group_id: str
    group_name: str
    device_ids: List[str]
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "group_id": "production_servers",
                "group_name": "生产服务器",
                "device_ids": ["server-001", "server-002", "server-003"],
                "metadata": {"environment": "production", "location": "datacenter"}
            }
        }


class DeviceGroupResponse(BaseModel):
    """设备分组响应"""
    group_id: str
    group_name: str
    device_count: int
    device_ids: List[str]
    metadata: Dict[str, Any]


class BatchProgressResponse(BaseModel):
    """批次进度响应"""
    batch_id: str
    total_devices: int
    successful: int
    failed: int
    progress_percentage: float
    status: str
    created_at: Optional[str] = None


class BatchListResponse(BaseModel):
    """批量任务列表响应"""
    batches: List[BatchProgressResponse]
    total: int


# ==================== API端点 ====================

@router.post(
    "",
    response_model=BatchTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="批量创建任务",
    description="支持批量调度任务到多个设备或设备分组"
)
async def create_batch_tasks(
    request: BatchTaskRequest,
    authorization: Optional[str] = Header(None)
):
    """
    批量创建任务 - Week 5-6核心功能

    **直接指定设备列表：**
    ```json
    {
      "name": "系统巡检",
      "command": "uptime && df -h",
      "device_ids": ["server-001", "server-002", "server-003"]
    }
    ```

    **使用设备分组：**
    ```json
    {
      "name": "服务器重启",
      "command": "reboot",
      "group_id": "production_servers",
      "parallel": false
    }
    ```
    """
    try:
        # 验证授权
        created_by = request.created_by
        if authorization:
            # 简单的token验证（生产环境应使用更安全的方式）
            if authorization.startswith("Bearer "):
                created_by = authorization[7:].strip()

        # 获取编排器
        orchestrator = get_orchestrator()

        # 构建任务规格
        task_spec = {
            'name': request.name,
            'command': request.command,
            'description': request.description or f"{request.name} - batch task",
            'created_by': created_by
        }

        # 执行批量调度
        if request.group_id:
            # 使用设备分组
            result = orchestrator.schedule_task_to_group(
                task_spec,
                request.group_id,
                parallel=request.parallel
            )
        elif request.device_ids:
            # 使用设备列表
            result = orchestrator.schedule_task_to_devices(
                task_spec,
                request.device_ids,
                parallel=request.parallel
            )
        else:
            # 直接抛出HTTPException，会被全局异常处理器转换为正确格式
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either device_ids or group_id must be provided"
            )

        # 获取批次进度
        progress = orchestrator.get_batch_progress(result.batch_id)

        # 构建响应
        return BatchTaskResponse(
            batch_id=result.batch_id,
            name=request.name,
            command=request.command,
            total_devices=result.total_devices,
            successful_schedules=result.successful_schedules,
            failed_schedules=result.failed_schedules,
            task_ids=result.task_ids,
            errors=result.errors,
            progress_percentage=progress['progress_percentage'],
            status=progress['status'],
            created_at=result.created_at.isoformat() if result.created_at else ""
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating batch tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/list",
    response_model=BatchListResponse,
    summary="列出批量任务",
    description="获取所有活跃批量任务的状态列表"
)
async def list_batch_tasks(
    limit: int = Query(20, ge=1, le=100, description="最大返回数量")
):
    """
    列出批量任务

    返回当前所有活跃批次的状态信息。
    """
    try:
        orchestrator = get_orchestrator()
        active_batches = orchestrator.get_active_batches()

        # 转换为响应格式
        batch_list = []
        for batch_id, result in list(active_batches.items())[:limit]:
            progress = orchestrator.get_batch_progress(batch_id)

            batch_list.append(BatchProgressResponse(
                batch_id=batch_id,
                total_devices=result.total_devices,
                successful=result.successful_schedules,
                failed=result.failed_schedules,
                progress_percentage=progress['progress_percentage'],
                status=progress['status'],
                created_at=result.created_at.isoformat() if result.created_at else None
            ))

        return BatchListResponse(
            batches=batch_list,
            total=len(batch_list)
        )

    except Exception as e:
        logger.error(f"Error listing batch tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/groups",
    response_model=List[DeviceGroupResponse],
    summary="列出设备分组",
    description="获取所有设备分组信息"
)
async def list_device_groups():
    """
    列出设备分组

    返回所有已创建的设备分组及其详细信息。
    """
    try:
        orchestrator = get_orchestrator()
        groups = orchestrator.get_device_groups()

        return [
            DeviceGroupResponse(
                group_id=group.group_id,
                group_name=group.group_name,
                device_count=len(group.device_ids),
                device_ids=group.device_ids,
                metadata=group.metadata
            )
            for group in groups.values()
        ]

    except Exception as e:
        logger.error(f"Error listing device groups: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "",
    response_model=BatchTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="批量创建任务",
    description="支持批量调度任务到多个设备或设备分组"
)
async def create_batch_tasks(
    request: BatchTaskRequest,
    authorization: Optional[str] = Header(None)
):
    """
    批量创建任务 - Week 5-6核心功能

    **直接指定设备列表：**
    ```json
    {
      "name": "系统巡检",
      "command": "uptime && df -h",
      "device_ids": ["server-001", "server-002", "server-003"]
    }
    ```

    **使用设备分组：**
    ```json
    {
      "name": "服务器重启",
      "command": "reboot",
      "group_id": "production_servers",
      "parallel": false
    }
    ```
    """
    try:
        # 验证授权
        created_by = request.created_by
        if authorization:
            # 简单的token验证（生产环境应使用更安全的方式）
            if authorization.startswith("Bearer "):
                created_by = authorization[7:].strip()

        # 获取编排器
        orchestrator = get_orchestrator()

        # 构建任务规格
        task_spec = {
            'name': request.name,
            'command': request.command,
            'description': request.description or f"{request.name} - batch task",
            'created_by': created_by
        }

        # 执行批量调度
        if request.group_id:
            # 使用设备分组
            result = orchestrator.schedule_task_to_group(
                task_spec,
                request.group_id,
                parallel=request.parallel
            )
        elif request.device_ids:
            # 使用设备列表
            result = orchestrator.schedule_task_to_devices(
                task_spec,
                request.device_ids,
                parallel=request.parallel
            )
        else:
            # 直接抛出HTTPException，会被全局异常处理器转换为正确格式
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either device_ids or group_id must be provided"
            )

        # 获取批次进度
        progress = orchestrator.get_batch_progress(result.batch_id)

        # 构建响应
        return BatchTaskResponse(
            batch_id=result.batch_id,
            name=request.name,
            command=request.command,
            total_devices=result.total_devices,
            successful_schedules=result.successful_schedules,
            failed_schedules=result.failed_schedules,
            task_ids=result.task_ids,
            errors=result.errors,
            progress_percentage=progress['progress_percentage'],
            status=progress['status'],
            created_at=result.created_at.isoformat() if result.created_at else ""
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating batch tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/list",
    response_model=BatchListResponse,
    summary="列出批量任务",
    description="获取所有活跃批量任务的状态列表"
)
async def list_batch_tasks(
    limit: int = Query(20, ge=1, le=100, description="最大返回数量")
):
    """
    列出批量任务

    返回当前所有活跃批次的状态信息。
    """
    try:
        orchestrator = get_orchestrator()
        active_batches = orchestrator.get_active_batches()

        # 转换为响应格式
        batch_list = []
        for batch_id, result in list(active_batches.items())[:limit]:
            progress = orchestrator.get_batch_progress(batch_id)

            batch_list.append(BatchProgressResponse(
                batch_id=batch_id,
                total_devices=result.total_devices,
                successful=result.successful_schedules,
                failed=result.failed_schedules,
                progress_percentage=progress['progress_percentage'],
                status=progress['status'],
                created_at=result.created_at.isoformat() if result.created_at else None
            ))

        return BatchListResponse(
            batches=batch_list,
            total=len(batch_list)
        )

    except Exception as e:
        logger.error(f"Error listing batch tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/groups",
    response_model=List[DeviceGroupResponse],
    summary="列出设备分组",
    description="获取所有设备分组信息"
)
async def list_device_groups():
    """
    列出设备分组

    返回所有已创建的设备分组及其详细信息。
    """
    try:
        orchestrator = get_orchestrator()
        groups = orchestrator.get_device_groups()

        return [
            DeviceGroupResponse(
                group_id=group.group_id,
                group_name=group.group_name,
                device_count=len(group.device_ids),
                device_ids=group.device_ids,
                metadata=group.metadata
            )
            for group in groups.values()
        ]

    except Exception as e:
        logger.error(f"Error listing device groups: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/{batch_id}",
    response_model=BatchTaskResponse,
    summary="查询批量任务状态",
    description="根据批次ID查询批量任务的执行状态和进度"
)
async def get_batch_task_status(batch_id: str):
    """
    查询批量任务状态

    - **batch_id**: 批次唯一标识

    返回该批次的详细状态信息，包括成功/失败统计、任务ID列表等。
    """
    try:
        orchestrator = get_orchestrator()
        result = orchestrator.get_batch_status(batch_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch '{batch_id}' not found"
            )

        # 获取进度信息
        progress = orchestrator.get_batch_progress(batch_id)

        # 查询任务详情
        task_details = []
        for task_id in result.task_ids:
            try:
                task = orchestrator.task_manager.get_task(task_id)
                if task:
                    task_details.append({
                        'task_id': task.task_id,
                        'name': task.name,
                        'status': task.status,
                        'target_device_id': task.target_device_id,
                        'command': task.command
                    })
            except Exception as e:
                logger.warning(f"Failed to get task {task_id}: {e}")

        # 重新构建task名称（取第一个任务的名称）
        name = task_details[0]['name'] if task_details else "Unknown Batch"
        command = task_details[0].get('command', '') if task_details else ''

        return BatchTaskResponse(
            batch_id=result.batch_id,
            name=name,
            command=command,
            total_devices=result.total_devices,
            successful_schedules=result.successful_schedules,
            failed_schedules=result.failed_schedules,
            task_ids=result.task_ids,
            errors=result.errors,
            progress_percentage=progress['progress_percentage'],
            status=progress['status'],
            created_at=result.created_at.isoformat() if result.created_at else ""
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/{batch_id}/progress",
    response_model=BatchProgressResponse,
    summary="查询批次进度",
    description="查询特定批次的执行进度信息"
)
async def get_batch_progress(batch_id: str):
    """
    查询批次进度

    返回批次执行的详细进度信息，包括百分比和当前状态。
    """
    try:
        orchestrator = get_orchestrator()
        progress = orchestrator.get_batch_progress(batch_id)

        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch '{batch_id}' not found"
            )

        return BatchProgressResponse(**progress)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/groups",
    response_model=DeviceGroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建设备分组",
    description="创建设备分组以便批量任务调度"
)
async def create_device_group(request: DeviceGroupRequest):
    """
    创建设备分组

    **示例：**
    ```json
    {
      "group_id": "production_servers",
      "group_name": "生产服务器",
      "device_ids": ["server-001", "server-002", "server-003"],
      "metadata": {"environment": "production"}
    }
    ```
    """
    try:
        orchestrator = get_orchestrator()

        group = orchestrator.create_device_group(
            request.group_id,
            request.group_name,
            request.device_ids,
            request.metadata
        )

        return DeviceGroupResponse(
            group_id=group.group_id,
            group_name=group.group_name,
            device_count=len(group.device_ids),
            device_ids=group.device_ids,
            metadata=group.metadata
        )

    except Exception as e:
        logger.error(f"Error creating device group: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除设备分组",
    description="删除指定的设备分组"
)
async def delete_device_group(group_id: str):
    """
    删除设备分组

    - **group_id**: 分组ID

    删除指定的设备分组，已创建的任务不会受影响。
    """
    try:
        orchestrator = get_orchestrator()
        success = orchestrator.remove_device_group(group_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device group '{group_id}' not found"
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting device group: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )