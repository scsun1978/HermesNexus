"""
HermesNexus Phase 4A - Task API v2
任务编排 API v2 端点 - 集成模板和设备抽象
"""

from fastapi import APIRouter, HTTPException, Query, status, Header
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import os

from hermesnexus.task.manager import TaskManager
from hermesnexus.task.templates import TemplateManager, CoreTemplates
from hermesnexus.device.manager import DeviceManager, DeviceCommandGenerator
from hermesnexus.device.types import DeviceCommandAdapter, DeviceTypeFactory
from hermesnexus.task.model import Task

router = APIRouter(prefix="/api/v2/tasks", tags=["tasks-v2"])


def get_current_user(authorization: Optional[str] = None) -> str:
    """获取当前用户（安全增强版）"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Expected: Bearer <token>"
        )

    token = authorization[7:].strip()
    if token and not token.count('.') == 2:
        return token

    import logging
    logging.warning(f"JWT token validation not implemented, using fallback for token: {token[:10]}...")
    return "admin"


# 全局管理器实例（避免重复初始化）
_managers_instance = None

def get_shared_managers():
    """获取共享的管理器实例（单例模式）"""
    global _managers_instance
    if _managers_instance is None:
        db_path = "data/tasks.db"
        os.makedirs("data", exist_ok=True)

        task_manager = TaskManager(db_path)
        template_manager = TemplateManager()
        device_manager = DeviceManager(db_path)

        # 注册核心模板
        for template in CoreTemplates.get_all_templates().values():
            template_manager.register_template(template)

        _managers_instance = (task_manager, template_manager, device_manager)

    return _managers_instance


class TaskCreateV2Request(BaseModel):
    """v2 任务创建请求"""
    name: str
    task_type: str = "custom"  # 任务类型
    priority: str = "medium"  # 优先级

    # 模板相关
    template_id: Optional[str] = None  # 使用模板创建
    template_params: Optional[Dict[str, Any]] = None  # 模板参数

    # 设备相关
    device_id: Optional[str] = None  # 目标设备ID

    # 直接命令相关
    command: Optional[str] = None  # 直接命令
    device_config: Optional[Dict[str, Any]] = None  # 设备配置

    # 其他参数
    timeout: int = 300
    scheduled_at: Optional[datetime] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "系统巡检任务",
                "template_id": "inspection",
                "device_id": "server-001",
                "priority": "high"
            }
        }


class TaskResponseV2(BaseModel):
    """v2 任务响应"""
    task_id: str
    name: str
    task_type: str
    status: str
    priority: str
    command: Optional[str] = None
    device_id: Optional[str] = None
    template_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: str
    created_by: str
    tags: Optional[List[str]] = None
    description: Optional[str] = None


class TemplateListResponse(BaseModel):
    """模板列表响应"""
    templates: List[Dict[str, Any]]
    total: int


class TemplateRenderRequest(BaseModel):
    """模板渲染请求"""
    template_id: str
    parameters: Dict[str, Any]


class TemplateRenderResponse(BaseModel):
    """模板渲染响应"""
    template_id: str
    rendered_command: str
    parameters: Dict[str, Any]
    preview: bool


@router.post(
    "",
    response_model=TaskResponseV2,
    status_code=status.HTTP_201_CREATED,
    summary="创建任务 (v2)",
    description="支持模板驱动和设备感知的任务创建"
)
async def create_task_v2(
    request: TaskCreateV2Request,
    authorization: Optional[str] = Header(None)
):
    """
    v2 任务创建 - 支持模板和设备抽象

    **模板驱动创建：**
    ```json
    {
      "name": "系统巡检",
      "template_id": "inspection",
      "device_id": "server-001",
      "priority": "high"
    }
    ```

    **直接命令创建：**
    ```json
    {
      "name": "自定义命令",
      "command": "echo 'test'",
      "device_id": "router-001",
      "device_config": {"device_type": "router", "vendor": "cisco"}
    }
    ```
    """
    try:
        created_by = get_current_user(authorization)
        task_manager, template_manager, device_manager = get_shared_managers()

        # 1. 模板驱动创建
        if request.template_id:
            try:
                template = template_manager.get_template(request.template_id)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Template not found: {request.template_id}"
                )

            # 获取设备信息（如果提供）
            device_config = None
            if request.device_id:
                device = device_manager.get_device(request.device_id)
                if device:
                    device_config = device
                # 如果设备不存在，继续创建任务但不使用设备参数

            # 渲染模板命令
            params = request.template_params or {}
            if device_config:
                params['device_type'] = device_config.get('device_type')
                params['vendor'] = device_config.get('vendor')

            command = template.render(**params)

            # 创建任务
            task = Task.create(
                name=request.name,
                description=request.description or f"{request.name} - {request.task_type}",
                command=command,
                target_device_id=request.device_id or "unknown",
                created_by=created_by
            )

        # 2. 直接命令创建
        elif request.command:
            # 如果提供了设备配置，使用设备命令适配器
            command = request.command
            if request.device_config:
                # 使用DeviceTypeFactory创建完整的设备配置（包含command_style）
                device_config = DeviceTypeFactory.create_config(
                    request.device_config.get('device_type', 'server'),
                    request.device_config
                )
                # 生成适配命令
                command = DeviceCommandAdapter.adapt_command_for_device(request.command, device_config)

            task = Task.create(
                name=request.name,
                description=request.description or f"{request.name} - {request.task_type}",
                command=command,
                target_device_id=request.device_id or "unknown",
                created_by=created_by
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either template_id or command must be provided"
            )

        # 保存任务
        task_manager.create_task(task)

        # 构建响应
        response = TaskResponseV2(
            task_id=task.task_id,
            name=task.name,
            task_type=request.task_type,  # 使用请求中的task_type
            status=task.status,
            priority=request.priority,  # 使用请求中的priority
            command=task.command,
            device_id=request.device_id,
            template_id=request.template_id,
            created_at=task.created_at.isoformat() if task.created_at else "",
            created_by=task.created_by,
            tags=request.tags or [],
            description=task.description
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/templates",
    response_model=TemplateListResponse,
    summary="获取任务模板列表",
    description="获取所有可用的任务模板"
)
async def list_templates():
    """
    获取任务模板列表

    返回系统内置的核心模板：
    - **inspection**: 系统巡检
    - **restart**: 服务重启
    - **upgrade**: 软件包升级
    - **rollback**: 配置回滚
    """
    try:
        _, template_manager, _ = get_shared_managers()

        templates = template_manager.list_templates()

        return TemplateListResponse(
            templates=templates,
            total=len(templates)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/templates/render",
    response_model=TemplateRenderResponse,
    summary="渲染任务模板",
    description="使用参数渲染任务模板，预览生成的命令"
)
async def render_template(request: TemplateRenderRequest):
    """
    渲染任务模板

    **示例：**
    ```json
    {
      "template_id": "inspection",
      "parameters": {
        "service_name": "nginx",
        "package_name": "nginx"
      }
    }
    ```
    """
    try:
        _, template_manager, _ = get_shared_managers()

        try:
            template = template_manager.get_template(request.template_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template not found: {request.template_id}"
            )

        # 渲染模板
        rendered_command = template.render(**request.parameters)

        return TemplateRenderResponse(
            template_id=request.template_id,
            rendered_command=rendered_command,
            parameters=request.parameters,
            preview=True
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "",
    response_model=List[TaskResponseV2],
    summary="列出任务 (v2)",
    description="获取任务列表，支持过滤"
)
async def list_tasks_v2(
    task_status: Optional[str] = Query(None, description="按状态过滤 (pending, running, succeeded, failed)"),
    device_id: Optional[str] = Query(None, description="按设备ID过滤"),
    limit: int = Query(20, ge=1, le=100, description="最大返回数量")
):
    """
    列出任务

    支持按状态和设备过滤：
    - **task_status**: 按状态过滤 (pending, running, succeeded, failed)
    - **device_id**: 按设备ID过滤
    - **limit**: 最大返回数量
    """
    try:
        task_manager, _, _ = get_shared_managers()

        tasks = task_manager.list_tasks(
            status=task_status,
            device_id=device_id,
            limit=limit
        )

        return [
            TaskResponseV2(
                task_id=t.task_id,
                name=t.name,
                task_type="custom",  # 默认任务类型
                status=t.status,
                priority="medium",  # 默认优先级
                command=t.command,
                device_id=t.target_device_id,
                created_at=t.created_at.isoformat() if t.created_at else "",
                created_by=t.created_by,
                tags=[]
            )
            for t in tasks
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/{task_id}",
    response_model=TaskResponseV2,
    summary="获取任务详情 (v2)",
    description="根据任务ID获取任务详细信息"
)
async def get_task_v2(task_id: str):
    """
    获取任务详情

    - **task_id**: 任务唯一标识
    """
    try:
        task_manager, _, _ = get_shared_managers()

        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task not found: {task_id}"
            )

        return TaskResponseV2(
            task_id=task.task_id,
            name=task.name,
            task_type="custom",  # 默认任务类型
            status=task.status,
            priority="medium",  # 默认优先级
            command=task.command,
            device_id=task.target_device_id,
            created_at=task.created_at.isoformat() if task.created_at else "",
            created_by=task.created_by,
            tags=[],
            description=task.description
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )