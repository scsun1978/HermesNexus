"""
FastAPI 应用主入口

提供云端 REST API 服务
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from contextlib import asynccontextmanager
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid
import os
from pathlib import Path

from shared.schemas.models import Node, Device, Job, Event, JobStatus, JobType, NodeStatus
from shared.protocol.messages import MessageType
from shared.protocol.error_codes import ErrorCode
from cloud.database.db import db

# 导入新的 API 路由
from cloud.api import task_api, asset_api

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
audit_logs_db: List[Dict] = []

# 锁和线程安全
import threading
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
    lifespan=lifespan
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
import os
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
        "console": "/console"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "1.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# 注册新的 API 路由
app.include_router(task_api.router, prefix="")
app.include_router(asset_api.router, prefix="")
# 也注册兼容的 jobs 路由
app.include_router(task_api.jobs_router, prefix="")


# 节点管理 API
# 节点管理 API
@app.get("/api/v1/nodes")
async def list_nodes(status: Optional[str] = None):
    """获取节点列表"""
    nodes_list = db.list_nodes()

    if status:
        nodes_list = [n for n in nodes_list if n.get("status") == status]

    return {
        "nodes": nodes_list,
        "total": len(nodes_list)
    }


@app.post("/api/v1/nodes/{node_id}/register")
async def register_node(node_id: str, registration_data: Dict[str, Any]):
    """注册新节点"""
    try:
        logger.info(f"📝 节点注册请求: {node_id}")

        # 检查节点是否已存在
        if db.get_node(node_id):
            # 更新现有节点
            db.update_node(node_id, {
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                "status": NodeStatus.ONLINE.value,
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "active_tasks": 0
            })

            # 记录审计日志
            db.add_audit_log({
                "action": "node_registered",
                "actor": node_id,
                "resource_type": "node",
                "resource_id": node_id,
                "details": {"registration_type": "update"},
                "success": True
            })

            logger.info(f"🔄 节点重新注册: {node_id}")
        else:
            # 创建新节点
            node_data = {
                "node_id": node_id,
                "name": registration_data.get("node_name", node_id),
                "status": NodeStatus.ONLINE.value,
                "capabilities": registration_data.get("capabilities", {}),
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "tags": ["ssh", "linux", "mvp"],
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "active_tasks": 0
            }

            db.add_node(node_id, node_data)

            # 记录事件
            db.add_event({
                "event_id": str(uuid.uuid4()),
                "type": "node_registered",
                "level": "info",
                "source": node_id,
                "source_type": "node",
                "message": f"节点 {node_id} 注册成功",
                "data": node_data
            })

            logger.info(f"✅ 新节点注册成功: {node_id}")

        return {
            "message": "节点注册成功",
            "node_id": node_id,
            "status": "online"
        }

    except Exception as e:
        logger.error(f"❌ 节点注册失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/nodes/{node_id}")
async def get_node(node_id: str):
    """获取节点详情"""
    node = db.get_node(node_id)
    if node:
        return node
    else:
        raise HTTPException(status_code=404, detail=f"节点不存在: {node_id}")


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
                "active_tasks": heartbeat_data.get("active_tasks", 0)
            }

            db.update_node(node_id, update_data)

            # 定期记录心跳事件 (避免过多事件)
            import random
            if random.random() < 0.1:  # 10%的概率记录事件
                db.add_event({
                    "event_id": str(uuid.uuid4()),
                    "type": "node_heartbeat",
                    "level": "info",
                    "source": node_id,
                    "source_type": "node",
                    "message": f"节点心跳: {node_id}",
                    "data": heartbeat_data
                })

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
                "created_by": job.get("created_by", "system")
            }
            tasks.append(task)

        logger.info(f"📋 节点 {node_id} 有 {len(tasks)} 个待处理任务")
        return {
            "tasks": tasks,
            "total": len(tasks)
        }

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
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            if result.get("error"):
                update_data["error_message"] = result.get("error")
            if result.get("error_code"):
                update_data["error_code"] = result.get("error_code")

            db.update_job(task_id, update_data)

            # 记录事件
            event_type = "job_completed" if result.get("status") == "success" else "job_failed"
            db.add_event({
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
                    "stderr": result.get("stderr", "")[:200]
                }
            })

            # 记录审计
            db.add_audit_log({
                "action": "job_completed" if result.get("status") == "success" else "job_failed",
                "actor": node_id,
                "resource_type": "job",
                "resource_id": task_id,
                "details": {
                    "node_id": node_id,
                    "status": result.get("status"),
                    "execution_time": result.get("execution_time", 0)
                },
                "success": result.get("status") == "success"
            })

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
        db.add_event({
            "event_id": str(uuid.uuid4()),
            "type": "error",
            "level": "error",
            "source": node_id,
            "source_type": "node",
            "title": f"节点错误: {error_data.get('error_code')}",
            "message": error_data.get("error_message", ""),
            "related_node_id": node_id,
            "data": error_data
        })

        # 记录审计
        db.add_audit_log({
            "action": "error_reported",
            "actor": node_id,
            "resource_type": "node",
            "resource_id": node_id,
            "details": error_data,
            "success": False
        })

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
        return {
            "devices": devices_list,
            "total": len(devices_list)
        }
    except Exception as e:
        logger.error(f"❌ 获取设备列表失败: {e}")
        return {
            "devices": [],
            "total": 0
        }


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
            db.add_event({
                "type": "device_created",
                "level": "info",
                "source": device.device_id,
                "source_type": "device",
                "message": f"设备 {device.device_id} 创建成功",
                "data": device_data
            })

            return {
                "message": "设备创建成功",
                "device_id": device.device_id
            }
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

        return {
            "jobs": jobs_list,
            "total": len(jobs_list),
            "limit": limit
        }

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
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        db.add_job(job_id, job)

        # 记录事件
        db.add_event({
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
                "node_id": node_id
            }
        })

        # 记录审计
        db.add_audit_log({
            "action": "create",
            "actor": job_data.get("created_by", "user"),
            "resource_type": "job",
            "resource_id": job_id,
            "details": job_data,
            "success": True
        })

        logger.info(f"✅ 任务创建成功: {job_id} -> 分配给节点 {node_id}")
        return {
            "message": "任务创建成功",
            "job_id": job_id,
            "status": "pending",
            "assigned_node": node_id
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
        db.update_job(job_id, {
            "status": "cancelled",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })

        # 记录事件
        db.add_event({
            "event_id": str(uuid.uuid4()),
            "type": "job_cancelled",
            "level": "info",
            "source": cancel_data.get("cancelled_by", "user"),
            "source_type": "user",
            "title": "任务已取消",
            "message": f"任务 {job_id} 被取消",
            "related_job_id": job_id,
            "related_node_id": job.get("node_id"),
            "data": {"reason": cancel_data.get("reason", "用户取消")}
        })

        logger.info(f"✅ 任务已取消: {job_id}")
        return {"message": "任务取消成功", "job_id": job_id, "status": "cancelled"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 事件查询 API
@app.get("/api/v1/events")
async def list_events(limit: int = 100, offset: int = 0, level: Optional[str] = None, event_type: Optional[str] = None):
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
        paginated_events = all_events[offset:offset + limit]

        # 获取总数
        total_count = len(db.events) if hasattr(db, 'events') else len(all_events)

        return {
            "events": paginated_events,
            "total": total_count,
            "limit": limit,
            "offset": offset
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
async def list_audit_logs(limit: int = 100, action: Optional[str] = None, actor: Optional[str] = None):
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
        total_count = len(db.audit_logs) if hasattr(db, 'audit_logs') else len(all_logs)

        return {
            "logs": all_logs,
            "total": total_count,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"❌ 获取审计日志失败: {e}")
        return {"logs": [], "total": 0, "limit": limit}


# 错误处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    logger.error(f"未处理的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "内部服务器错误"}
    )


# 开发服务器启动
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
