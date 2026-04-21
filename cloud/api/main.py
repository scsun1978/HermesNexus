"""
FastAPI 应用主入口

提供云端 REST API 服务
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import threading
import uvicorn
from contextlib import asynccontextmanager
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid
import os

from shared.schemas.models import (
    Device,
    JobStatus,
    JobType,
    NodeStatus,
)
from cloud.database.db import db

# 导入新的 API 路由
from cloud.api import task_api, asset_api

# Phase 4 Day 4-5: 导入v2 API
from cloud.api import task_v2_api

# Week 5-6: 导入批量任务API
from cloud.api import batch_api

# Phase 4 Day 2: 导入监控API
from cloud.api import monitoring_api

# Phase 3 Day 3: 导入审批API
from cloud.api import approval_api

# Phase 3 Day 4: 导入回滚API
from cloud.api import rollback_api

# Phase 3: 导入节点认证相关模块
from shared.security.node_token_service import get_node_token_service

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
audit_logs_db: List[Dict] = []

# 锁和线程安全
db_lock = threading.Lock()


# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动和关闭管理"""
    logger.info("🚀 HermesNexus Cloud API 启动中...")
    # 启动时初始化
    yield
    logger.info("👋 HermesNexus Cloud API 关闭中...")


# 创建 FastAPI 应用
app = FastAPI(
    title="HermesNexus Cloud API",
    description="分布式边缘设备管理系统 - 云端控制平面",
    version="1.1.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件

# 获取项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
console_path = os.path.join(project_root, "console")
static_path = os.path.join(console_path, "static")

if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

    @app.get("/console")
    async def console():
        """控制台页面"""
        from fastapi.responses import FileResponse

        index_path = os.path.join(console_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            raise HTTPException(status_code=404, detail="控制台页面未找到")


# 基础路由
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "HermesNexus Cloud API",
        "version": "1.1.0",
        "status": "running",
        "console": "/console",
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "1.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# 注册新的 API 路由
app.include_router(task_api.router, prefix="")
app.include_router(asset_api.router, prefix="")

# Phase 4 Day 4-5: 注册v2 API路由
app.include_router(task_v2_api.router, prefix="")

# Week 5-6: 注册批量任务API路由
app.include_router(batch_api.router, prefix="")

# Phase 3 Day 3: 注册审批API路由
app.include_router(approval_api.router, prefix="")
# Phase 3 Day 4: 注册回滚API路由
app.include_router(rollback_api.router, prefix="")

# Phase 4 Day 2: 注册监控API路由
app.include_router(monitoring_api.router, prefix="")


# 节点管理 API
# 节点管理 API
@app.get("/api/v1/nodes")
async def list_nodes(status: Optional[str] = None):
    """获取节点列表 (旧接口，向后兼容)"""
    nodes_list = db.list_nodes()

    if status:
        nodes_list = [n for n in nodes_list if n.get("status") == status]

    return {"nodes": nodes_list, "total": len(nodes_list)}


@app.post("/api/v1/nodes/query")
async def query_nodes(request: Dict[str, Any]):
    """增强节点列表查询 - v1.2 支持分页、筛选、排序"""
    try:
        from shared.models.node_list import NodeListRequest
        from shared.services.node_list_service import get_node_list_service

        # 构建查询请求
        query_request = NodeListRequest(
            page=request.get("page", 1),
            page_size=request.get("page_size", 20),
            filters=request.get("filters", {}),
            status=request.get("status"),
            node_type=request.get("node_type"),
            tags=request.get("tags"),
            location=request.get("location"),
            search=request.get("search"),
            heartbeat_after=request.get("heartbeat_after"),
            heartbeat_before=request.get("heartbeat_before"),
            created_after=request.get("created_after"),
            created_before=request.get("created_before"),
            sort_by=request.get("sort_by", "created_at"),
            sort_order=request.get("sort_order", "desc"),
            include_heartbeat_stats=request.get("include_heartbeat_stats", False),
            include_task_summary=request.get("include_task_summary", False),
            include_audit_summary=request.get("include_audit_summary", False),
        )

        # 查询节点列表
        service = get_node_list_service()
        result = service.get_node_list(query_request)

        logger.info(f"✅ 查询节点列表: page={query_request.page}, found={result.total} nodes")

        return result.dict()

    except Exception as e:
        logger.error(f"❌ 查询节点列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/nodes/batch")
async def get_nodes_batch(request: Dict[str, Any]):
    """批量获取节点详情 - v1.2 支持批量查询和增强信息"""
    try:
        from shared.models.node_list import BatchNodeRequest
        from shared.services.node_list_service import get_node_list_service

        # 构建批量请求
        batch_request = BatchNodeRequest(
            node_ids=request.get("node_ids", []),
            include_heartbeat_stats=request.get("include_heartbeat_stats", False),
            include_task_summary=request.get("include_task_summary", False),
            include_audit_summary=request.get("include_audit_summary", False),
        )

        # 批量查询节点
        service = get_node_list_service()
        result = service.get_nodes_batch(batch_request)

        logger.info(
            f"✅ 批量查询节点: requested={len(batch_request.node_ids)}, found={result.found_nodes}"
        )

        return result.dict()

    except Exception as e:
        logger.error(f"❌ 批量查询节点失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/nodes/{node_id}/register")
async def register_node(node_id: str, registration_data: Dict[str, Any]):
    """注册新节点 - Phase 3: 增强版，支持Token颁发"""
    try:
        logger.info(f"📝 节点注册请求: {node_id}")

        # Phase 3: 创建节点身份对象
        from shared.models.node import NodeType, NodeIdentity

        node_identity = NodeIdentity(
            node_id=node_id,
            node_name=registration_data.get("node_name", node_id),
            node_type=NodeType(registration_data.get("node_type", "physical")),
            status=NodeStatus.REGISTERED,
            tenant_id=registration_data.get("tenant_id", "default"),
            region_id=registration_data.get("region_id", "default"),
            capabilities=registration_data.get("capabilities", {}),
            max_concurrent_tasks=registration_data.get("max_concurrent_tasks", 3),
            description=registration_data.get("description", ""),
            location=registration_data.get("location", ""),
            tags=registration_data.get("tags", []),
            metadata=registration_data.get("metadata", {}),
            registered_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )

        # 检查节点是否已存在
        existing_node = db.get_node(node_id)
        if existing_node:
            # 更新现有节点
            db.update_node(
                node_id,
                {
                    "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                    "status": NodeStatus.ACTIVE.value,
                    "cpu_usage": 0.0,
                    "memory_usage": 0.0,
                    "active_tasks": 0,
                },
            )

            # Phase 3: 为现有节点重新颁发Token
            token_service = get_node_token_service()
            token_info = token_service.generate_token(node_identity)

            # 记录审计日志
            db.add_audit_log(
                {
                    "action": "node_registered",
                    "actor": node_id,
                    "resource_type": "node",
                    "resource_id": node_id,
                    "details": {"registration_type": "update", "token_refreshed": True},
                    "success": True,
                }
            )

            logger.info(f"🔄 节点重新注册并刷新Token: {node_id}")

            return {
                "message": "节点重新注册成功",
                "node_id": node_id,
                "status": "active",
                "token": token_info.token,  # Phase 3: 迷新Token
                "expires_at": token_info.expires_at.isoformat(),
            }
        else:
            # 创建新节点
            node_data = {
                "node_id": node_id,
                "name": registration_data.get("node_name", node_id),
                "status": NodeStatus.REGISTERED.value,
                "capabilities": registration_data.get("capabilities", {}),
                "max_concurrent_tasks": registration_data.get("max_concurrent_tasks", 3),
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "tags": ["ssh", "linux", "mvp"],
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "active_tasks": 0,
            }

            db.add_node(node_id, node_data)

            # Phase 3: 为新节点颁发Token
            token_service = get_node_token_service()
            token_info = token_service.generate_token(node_identity)

            # 记录事件
            db.add_event(
                {
                    "event_id": str(uuid.uuid4()),
                    "type": "node_registered",
                    "level": "info",
                    "source": node_id,
                    "source_type": "node",
                    "message": f"节点 {node_id} 注册成功",
                    "data": {
                        "node_name": node_identity.node_name,
                        "node_type": node_identity.node_type.value,
                        "token_issued": True,
                    },
                }
            )

            # 记录审计
            db.add_audit_log(
                {
                    "action": "create",
                    "actor": "system",
                    "resource_type": "node",
                    "resource_id": node_id,
                    "details": registration_data,
                    "success": True,
                }
            )

            logger.info(f"✅ 新节点注册成功: {node_id}")

            return {
                "message": "节点注册成功",
                "node_id": node_id,
                "status": "registered",
                "token": token_info.token,  # Phase 3: 返回Token
                "expires_at": token_info.expires_at.isoformat(),
                "permissions": token_info.permissions,
            }

    except Exception as e:
        logger.error(f"❌ 节点注册失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    except Exception as e:
        logger.error(f"❌ 节点注册失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/nodes/{node_id}")
async def get_node(node_id: str, include_details: bool = False):
    """获取节点详情 - v1.2 支持增强信息"""
    try:
        # 基础节点信息
        node = db.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail=f"节点不存在: {node_id}")

        # 如果不要求详细信息，直接返回
        if not include_details:
            return node

        # 增强节点信息
        from shared.services.node_list_service import get_node_list_service
        from shared.models.node import NodeIdentity

        service = get_node_list_service()

        # 将字典转换为NodeIdentity对象
        node_identity = NodeIdentity(**node)

        # 增强节点数据
        enhanced_node = service._enhance_node_data(
            node_identity,
            include_heartbeat_stats=True,
            include_task_summary=True,
            include_audit_summary=True,
        )

        logger.info(f"✅ 获取节点详情: {node_id}")

        return enhanced_node

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取节点详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/nodes/{node_id}/heartbeat")
async def receive_heartbeat(node_id: str, heartbeat_data: Dict[str, Any]):
    """接收节点心跳"""
    try:
        # 更新节点心跳信息
        if db.get_node(node_id):
            update_data = {
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                "status": heartbeat_data.get("status", "online"),
                "cpu_usage": heartbeat_data.get("cpu_usage", 0.0),
                "memory_usage": heartbeat_data.get("memory_usage", 0.0),
                "active_tasks": heartbeat_data.get("active_tasks", 0),
            }

            db.update_node(node_id, update_data)

            # 定期记录心跳事件 (避免过多事件)
            import random

            if random.random() < 0.1:  # 10%的概率记录事件
                db.add_event(
                    {
                        "event_id": str(uuid.uuid4()),
                        "type": "node_heartbeat",
                        "level": "info",
                        "source": node_id,
                        "source_type": "node",
                        "message": f"节点心跳: {node_id}",
                        "data": heartbeat_data,
                    }
                )

            logger.debug(f"💓 收到节点心跳: {node_id}")
            return {"status": "received"}
        else:
            raise HTTPException(status_code=404, detail=f"节点不存在: {node_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 处理心跳失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/nodes/{node_id}/tasks")
async def get_node_tasks(node_id: str, status: Optional[str] = None):
    """获取节点的待处理任务"""
    try:
        # 查找分配给该节点的待处理任务
        jobs = db.list_jobs(status="pending", node_id=node_id)

        # 转换为任务消息格式
        tasks = []
        for job in jobs:
            task = {
                "task_id": job["job_id"],
                "job_id": job["job_id"],
                "task_type": job.get("task_type", "exec"),
                "target_device_id": job.get("target_device_id", ""),
                "target_host": job.get("target_host", ""),
                "command": job.get("command", ""),
                "script": job.get("script", ""),
                "parameters": job.get("parameters", {}),
                "timeout": job.get("timeout", 300),
                "priority": job.get("priority", "normal"),
                "created_by": job.get("created_by", "system"),
            }
            tasks.append(task)

        logger.info(f"📋 节点 {node_id} 有 {len(tasks)} 个待处理任务")
        return {"tasks": tasks, "total": len(tasks)}

    except Exception as e:
        logger.error(f"❌ 获取节点任务失败: {e}")
        return {"tasks": [], "total": 0}


@app.post("/api/v1/nodes/{node_id}/tasks/{task_id}/result")
async def receive_task_result(node_id: str, task_id: str, result: Dict[str, Any]):
    """接收任务执行结果"""
    try:
        logger.info(f"📥 收到任务结果: {node_id}/{task_id} - {result.get('status')}")

        # 更新任务状态
        if db.get_job(task_id):
            update_data = {
                "status": result.get("status", "failed"),
                "result": result,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            if result.get("error"):
                update_data["error_message"] = result.get("error")
            if result.get("error_code"):
                update_data["error_code"] = result.get("error_code")

            db.update_job(task_id, update_data)

            # 记录事件
            event_type = "job_completed" if result.get("status") == "success" else "job_failed"
            db.add_event(
                {
                    "event_id": str(uuid.uuid4()),
                    "type": event_type,
                    "level": "info" if result.get("status") == "success" else "error",
                    "source": node_id,
                    "source_type": "node",
                    "title": f"任务 {event_type}",
                    "message": f"任务 {task_id} {result.get('status')}",
                    "related_job_id": task_id,
                    "related_node_id": node_id,
                    "data": {
                        "task_id": task_id,
                        "status": result.get("status"),
                        "execution_time": result.get("execution_time", 0),
                        "exit_code": result.get("exit_code"),
                        "stdout": result.get("stdout", "")[:200],  # 只保留前200字符
                        "stderr": result.get("stderr", "")[:200],
                    },
                }
            )

            # 记录审计
            db.add_audit_log(
                {
                    "action": (
                        "job_completed" if result.get("status") == "success" else "job_failed"
                    ),
                    "actor": node_id,
                    "resource_type": "job",
                    "resource_id": task_id,
                    "details": {
                        "node_id": node_id,
                        "status": result.get("status"),
                        "execution_time": result.get("execution_time", 0),
                    },
                    "success": result.get("status") == "success",
                }
            )

            logger.info(f"✅ 任务结果已记录: {task_id} -> {result.get('status')}")
            return {"status": "recorded"}

        else:
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 记录任务结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/nodes/{node_id}/errors")
async def receive_node_error(node_id: str, error_data: Dict[str, Any]):
    """接收节点错误报告"""
    try:
        logger.error(f"❌ 节点错误报告: {node_id} - {error_data.get('error_code')}")

        # 记录错误事件
        db.add_event(
            {
                "event_id": str(uuid.uuid4()),
                "type": "error",
                "level": "error",
                "source": node_id,
                "source_type": "node",
                "title": f"节点错误: {error_data.get('error_code')}",
                "message": error_data.get("error_message", ""),
                "related_node_id": node_id,
                "data": error_data,
            }
        )

        # 记录审计
        db.add_audit_log(
            {
                "action": "error_reported",
                "actor": node_id,
                "resource_type": "node",
                "resource_id": node_id,
                "details": error_data,
                "success": False,
            }
        )

        return {"status": "recorded"}

    except Exception as e:
        logger.error(f"❌ 处理错误报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 设备管理 API
@app.get("/api/v1/devices")
async def list_devices():
    """获取设备列表"""
    try:
        devices_list = db.list_devices()
        return {"devices": devices_list, "total": len(devices_list)}
    except Exception as e:
        logger.error(f"❌ 获取设备列表失败: {e}")
        return {"devices": [], "total": 0}


@app.post("/api/v1/devices")
async def create_device(device: Device):
    """创建新设备"""
    try:
        logger.info(f"创建设备: {device.device_id}")

        # 检查设备是否已存在
        if db.get_device(device.device_id):
            raise HTTPException(status_code=400, detail="设备已存在")

        # 创建设备记录
        device_data = device.model_dump()
        logger.info(f"设备数据: {device_data}")
        logger.info(f"调用db.add_device前，设备列表长度: {len(db.list_devices())}")
        success = db.add_device(device.device_id, device_data)
        logger.info(f"调用db.add_device后，设备列表长度: {len(db.list_devices())}")
        logger.info(f"add_device返回结果: {success}")

        if success:
            # 记录事件日志
            db.add_event(
                {
                    "type": "device_created",
                    "level": "info",
                    "source": device.device_id,
                    "source_type": "device",
                    "message": f"设备 {device.device_id} 创建成功",
                    "data": device_data,
                }
            )

            return {"message": "设备创建成功", "device_id": device.device_id}
        else:
            raise HTTPException(status_code=500, detail="设备创建失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建设备失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建设备失败: {str(e)}")


# 任务管理 API
@app.get("/api/v1/jobs")
async def list_jobs(status: Optional[str] = None, node_id: Optional[str] = None, limit: int = 100):
    """获取任务列表"""
    try:
        jobs_list = db.list_jobs(status=status, node_id=node_id)

        # 分页支持
        if len(jobs_list) > limit:
            jobs_list = jobs_list[:limit]

        return {"jobs": jobs_list, "total": len(jobs_list), "limit": limit}

    except Exception as e:
        logger.error(f"❌ 获取任务列表失败: {e}")
        return {"jobs": [], "total": 0, "limit": limit}


@app.post("/api/v1/jobs")
async def create_job(job_data: Dict[str, Any]):
    """创建新任务"""
    try:
        job_id = job_data.get("job_id", f"job-{str(uuid.uuid4())}")

        logger.info(f"📝 创建任务: {job_id}")

        # 验证必填字段
        if not job_data.get("target_device_id"):
            raise HTTPException(status_code=400, detail="缺少target_device_id")

        if not job_data.get("command") and not job_data.get("script"):
            raise HTTPException(status_code=400, detail="必须提供command或script")

        # 获取目标设备
        device = db.get_device(job_data["target_device_id"])
        if not device:
            raise HTTPException(status_code=404, detail=f"设备不存在: {job_data['target_device_id']}")

        # 获取分配的节点 (简单轮询)
        available_nodes = db.list_nodes(status="online")
        if not available_nodes:
            raise HTTPException(status_code=400, detail="没有可用的在线节点")

        # 简单分配策略：选择第一个在线节点
        assigned_node = available_nodes[0]
        node_id = assigned_node["node_id"]

        # 创建任务记录
        job = {
            "job_id": job_id,
            "name": job_data.get("name", "未命名任务"),
            "type": job_data.get("type", JobType.BASIC_EXEC.value),
            "status": JobStatus.PENDING.value,
            "target_device_id": job_data["target_device_id"],
            "target_device_name": device.get("name", job_data["target_device_id"]),
            "task_type": job_data.get("task_type", "exec"),
            "command": job_data.get("command", ""),
            "script": job_data.get("script", ""),
            "parameters": job_data.get("parameters", {}),
            "priority": job_data.get("priority", "normal"),
            "timeout": job_data.get("timeout", 300),
            "node_id": node_id,
            "target_host": device.get("host", ""),
            "created_by": job_data.get("created_by", "user"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        db.add_job(job_id, job)

        # 记录事件
        db.add_event(
            {
                "event_id": str(uuid.uuid4()),
                "type": "job_created",
                "level": "info",
                "source": "cloud",
                "source_type": "cloud",
                "title": "任务创建",
                "message": f"任务 {job_id} 已创建",
                "related_job_id": job_id,
                "related_node_id": node_id,
                "related_device_id": job_data["target_device_id"],
                "data": {
                    "job_id": job_id,
                    "command": job.get("command"),
                    "node_id": node_id,
                },
            }
        )

        # 记录审计
        db.add_audit_log(
            {
                "action": "create",
                "actor": job_data.get("created_by", "user"),
                "resource_type": "job",
                "resource_id": job_id,
                "details": job_data,
                "success": True,
            }
        )

        logger.info(f"✅ 任务创建成功: {job_id} -> 分配给节点 {node_id}")
        return {
            "message": "任务创建成功",
            "job_id": job_id,
            "status": "pending",
            "assigned_node": node_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/jobs/{job_id}")
async def get_job(job_id: str):
    """获取任务详情"""
    job = db.get_job(job_id)
    if job:
        return job
    else:
        raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")


@app.patch("/api/v1/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, cancel_data: Dict[str, Any]):
    """取消任务"""
    try:
        job = db.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")

        # 只能取消pending或running状态的任务
        if job["status"] not in ["pending", "running"]:
            raise HTTPException(status_code=400, detail="任务状态不允许取消")

        # 更新任务状态
        db.update_job(
            job_id,
            {
                "status": "cancelled",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        # 记录事件
        db.add_event(
            {
                "event_id": str(uuid.uuid4()),
                "type": "job_cancelled",
                "level": "info",
                "source": cancel_data.get("cancelled_by", "user"),
                "source_type": "user",
                "title": "任务已取消",
                "message": f"任务 {job_id} 被取消",
                "related_job_id": job_id,
                "related_node_id": job.get("node_id"),
                "data": {"reason": cancel_data.get("reason", "用户取消")},
            }
        )

        logger.info(f"✅ 任务已取消: {job_id}")
        return {"message": "任务取消成功", "job_id": job_id, "status": "cancelled"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 事件查询 API
@app.get("/api/v1/events")
async def list_events(
    limit: int = 100,
    offset: int = 0,
    level: Optional[str] = None,
    event_type: Optional[str] = None,
):
    """获取事件列表"""
    try:
        # 获取所有事件，然后过滤
        all_events = db.list_events(limit=limit + offset)

        # 按类型过滤
        if event_type:
            all_events = [e for e in all_events if e.get("type") == event_type]

        # 按级别过滤
        if level:
            all_events = [e for e in all_events if e.get("level") == level]

        # 分页支持
        paginated_events = all_events[offset : offset + limit]

        # 获取总数
        total_count = len(db.events) if hasattr(db, "events") else len(all_events)

        return {
            "events": paginated_events,
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"❌ 获取事件列表失败: {e}")
        return {"events": [], "total": 0, "limit": limit, "offset": offset}


# 统计信息 API
@app.get("/api/v1/stats")
async def get_stats():
    """获取系统统计信息"""
    try:
        stats = db.get_stats()
        return stats

    except Exception as e:
        logger.error(f"❌ 获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 审计日志 API
@app.get("/api/v1/audit/logs")
async def list_audit_logs(
    limit: int = 100, action: Optional[str] = None, actor: Optional[str] = None
):
    """获取审计日志"""
    try:
        # 获取所有审计日志，然后过滤
        all_logs = db.list_audit_logs(limit=limit)

        # 按action过滤
        if action:
            all_logs = [log for log in all_logs if log.get("action") == action]

        # 按actor过滤
        if actor:
            all_logs = [log for log in all_logs if log.get("actor") == actor]

        # 获取总数
        total_count = len(db.audit_logs) if hasattr(db, "audit_logs") else len(all_logs)

        return {"logs": all_logs, "total": total_count, "limit": limit}

    except Exception as e:
        logger.error(f"❌ 获取审计日志失败: {e}")
        return {"logs": [], "total": 0, "limit": limit}


# 审计回放 API
@app.post("/api/v1/audit/{audit_id}/replay")
async def replay_audit_log(audit_id: str, replay_request: Dict[str, Any]):
    """回放审计日志"""
    try:
        from shared.services.audit_replay_service import get_replay_service, ReplayMode

        # 获取回放服务
        replay_service = get_replay_service(db)

        # 解析回放参数
        mode_str = replay_request.get("mode", "simulation")
        actor = replay_request.get("actor", "api_user")
        overrides = replay_request.get("overrides", {})

        # 转换回放模式
        try:
            mode = ReplayMode(mode_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的回放模式: {mode_str}. 可用模式: simulation, validation, execution",
            )

        logger.info(f"🔄 开始审计回放: {audit_id} (模式: {mode_str})")

        # 执行回放
        result = replay_service.replay_audit_log(
            audit_id=audit_id,
            mode=mode,
            actor=actor,
            overrides=overrides,
        )

        # 记录回放操作的审计日志
        db.add_audit_log(
            {
                "action": "audit_replay",
                "actor": actor,
                "resource_type": "audit_log",
                "resource_id": audit_id,
                "details": {
                    "replay_mode": mode_str,
                    "replay_result": result.get("success", False),
                    "replay_id": result.get("replay_id"),
                },
                "success": result.get("success", False),
            }
        )

        if result.get("success"):
            logger.info(f"✅ 审计回放成功: {result.get('replay_id')}")
            return result
        else:
            logger.warning(f"⚠️  审计回放失败: {result.get('error')}")
            raise HTTPException(status_code=400, detail=result.get("error"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 审计回放失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/audit/{audit_id}/replay-capability")
async def check_replay_capability(audit_id: str):
    """检查审计日志是否支持回放"""
    try:
        from shared.services.audit_replay_service import get_replay_service

        replay_service = get_replay_service(db)

        # 获取原始审计日志
        original_audit = db.get_audit_log(audit_id)
        if not original_audit:
            raise HTTPException(status_code=404, detail=f"审计日志不存在: {audit_id}")

        # 检查回放能力
        capability = replay_service._check_replay_capability(original_audit)

        return {
            "audit_id": audit_id,
            "can_replay": capability["can_replay"],
            "reason": capability["reason"],
            "action": original_audit.get("action"),
            "target_type": original_audit.get("target_type"),
            "target_id": original_audit.get("target_id"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 检查回放能力失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 错误处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 异常处理"""
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


# ==================== 批量操作 API ====================


@app.post("/api/v1/batch/assets")
async def batch_assets_operation(request_data: Dict[str, Any]):
    """批量资产操作 - v1.2 支持创建、更新、删除"""
    try:
        from shared.models.batch_operations import (
            AssetBatchCreateRequest,
            AssetBatchUpdateRequest,
        )
        from shared.services.batch_operation_service import get_batch_operation_service

        operation = request_data.get("operation", "create")
        service = get_batch_operation_service(db)

        if operation == "create":
            request = AssetBatchCreateRequest(**request_data)
            result = await service.create_assets_batch(request)
        elif operation == "update":
            request = AssetBatchUpdateRequest(**request_data)
            result = await service.update_assets_batch(request)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的操作类型: {operation}")

        logger.info(f"✅ 批量资产操作完成: {operation}, operation_id={result.operation_id}")

        return result.dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 批量资产操作失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/batch/assets/create")
async def batch_create_assets(request_data: Dict[str, Any]):
    """批量创建资产"""
    try:
        from shared.models.batch_operations import AssetBatchCreateRequest
        from shared.services.batch_operation_service import get_batch_operation_service

        request = AssetBatchCreateRequest(**request_data)
        service = get_batch_operation_service(db)
        result = await service.create_assets_batch(request)

        logger.info(f"✅ 批量创建资产完成: operation_id={result.operation_id}")

        return result.dict()

    except Exception as e:
        logger.error(f"❌ 批量创建资产失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/batch/assets/update")
async def batch_update_assets(request_data: Dict[str, Any]):
    """批量更新资产"""
    try:
        from shared.models.batch_operations import AssetBatchUpdateRequest
        from shared.services.batch_operation_service import get_batch_operation_service

        request = AssetBatchUpdateRequest(**request_data)
        service = get_batch_operation_service(db)
        result = await service.update_assets_batch(request)

        logger.info(f"✅ 批量更新资产完成: operation_id={result.operation_id}")

        return result.dict()

    except Exception as e:
        logger.error(f"❌ 批量更新资产失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/batch/assets/delete")
async def batch_delete_assets(request_data: Dict[str, Any]):
    """批量删除资产"""
    try:
        from shared.models.batch_operations import AssetBatchDeleteRequest
        from shared.services.batch_operation_service import get_batch_operation_service

        request = AssetBatchDeleteRequest(**request_data)
        service = get_batch_operation_service(db)
        result = await service.delete_assets_batch(request)

        logger.info(f"✅ 批量删除资产完成: operation_id={result.operation_id}")

        return result.dict()

    except Exception as e:
        logger.error(f"❌ 批量删除资产失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/batch/assets/deactivate")
async def batch_deactivate_assets(request_data: Dict[str, Any]):
    """批量停用资产"""
    try:
        from shared.services.batch_operation_service import get_batch_operation_service

        asset_ids = request_data.get("asset_ids", [])
        stop_on_first_error = request_data.get("stop_on_first_error", False)
        idempotency_key = request_data.get("idempotency_key")
        user_id = request_data.get("user_id")
        username = request_data.get("username")
        request_ip = request_data.get("request_ip")
        user_agent = request_data.get("user_agent")

        service = get_batch_operation_service(db)
        result = await service.deactivate_assets_batch(
            asset_ids=asset_ids,
            stop_on_first_error=stop_on_first_error,
            idempotency_key=idempotency_key,
            user_id=user_id,
            username=username,
            request_ip=request_ip,
            user_agent=user_agent,
        )

        logger.info(f"✅ 批量停用资产完成: operation_id={result.operation_id}")

        return result.dict()

    except Exception as e:
        logger.error(f"❌ 批量停用资产失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/batch/tasks")
async def batch_tasks_operation(request_data: Dict[str, Any]):
    """批量任务操作 - v1.2 支持创建、下发、取消"""
    try:
        from shared.models.batch_operations import TaskBatchCreateRequest
        from shared.services.batch_operation_service import get_batch_operation_service

        operation = request_data.get("operation", "create")
        service = get_batch_operation_service(db)

        if operation == "create":
            request = TaskBatchCreateRequest(**request_data)
            result = await service.create_tasks_batch(request)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的操作类型: {operation}")

        logger.info(f"✅ 批量任务操作完成: {operation}, operation_id={result.operation_id}")

        return result.dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 批量任务操作失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/batch/tasks/create")
async def batch_create_tasks(request_data: Dict[str, Any]):
    """批量创建任务"""
    try:
        from shared.models.batch_operations import TaskBatchCreateRequest
        from shared.services.batch_operation_service import get_batch_operation_service

        request = TaskBatchCreateRequest(**request_data)
        service = get_batch_operation_service(db)
        result = await service.create_tasks_batch(request)

        logger.info(f"✅ 批量创建任务完成: operation_id={result.operation_id}")

        return result.dict()

    except Exception as e:
        logger.error(f"❌ 批量创建任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/batch/tasks/dispatch")
async def batch_dispatch_tasks(request_data: Dict[str, Any]):
    """批量下发任务"""
    try:
        from shared.models.batch_operations import TaskBatchDispatchRequest
        from shared.services.batch_operation_service import get_batch_operation_service

        request = TaskBatchDispatchRequest(**request_data)
        service = get_batch_operation_service(db)
        result = await service.dispatch_tasks_batch(request)

        logger.info(f"✅ 批量下发任务完成: operation_id={result.operation_id}")

        return result.dict()

    except Exception as e:
        logger.error(f"❌ 批量下发任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/batch/operations/{operation_id}")
async def get_batch_operation(operation_id: str):
    """获取批量操作状态"""
    try:
        from shared.services.batch_operation_service import get_batch_operation_service

        service = get_batch_operation_service(db)

        # 从历史记录中获取操作结果
        if operation_id in service._operation_history:
            return service._operation_history[operation_id].dict()
        else:
            raise HTTPException(status_code=404, detail=f"操作不存在: {operation_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取批量操作状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    logger.error(f"未处理的异常: {exc}")
    return JSONResponse(status_code=500, content={"error": "内部服务器错误"})


# 开发服务器启动
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True, log_level="info")
