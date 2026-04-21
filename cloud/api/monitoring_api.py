"""
HermesNexus Monitoring API
监控和指标API端点
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from typing import Dict, Any
from datetime import datetime, timezone
import psutil
import os
import time

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# 启动时间
_start_time = time.time()


@router.get("/health")
async def health_check():
    """
    详细健康检查端点

    Returns:
        系统健康状态详情
    """
    try:
        # 检查数据库连接
        from cloud.database.db import db
        db_health = "healthy"
        try:
            # 简单的数据库连接测试
            db.list_nodes()
        except Exception as e:
            db_health = f"unhealthy: {str(e)}"

        # 检查内存使用
        memory = psutil.virtual_memory()
        memory_health = "healthy" if memory.percent < 90 else "warning"

        # 检查磁盘使用
        disk = psutil.disk_usage('/')
        disk_health = "healthy" if disk.percent < 90 else "warning"

        overall_health = "healthy"
        if "unhealthy" in [db_health, memory_health, disk_health]:
            overall_health = "unhealthy"
        elif "warning" in [db_health, memory_health, disk_health]:
            overall_health = "degraded"

        return {
            "status": overall_health,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": time.time() - _start_time,
            "components": {
                "database": db_health,
                "memory": memory_health,
                "disk": disk_health
            },
            "system": {
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "cpu_percent": psutil.cpu_percent(interval=1)
            },
            "version": "1.2.0"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@router.get("/metrics")
async def metrics():
    """
    Prometheus格式的指标导出端点

    Returns:
        Prometheus格式的指标文本
    """
    try:
        # 系统指标
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # 应用指标
        uptime = time.time() - _start_time

        # 构建Prometheus格式的指标
        metrics_text = f"""# HELP hermes_system_cpu_percent CPU使用百分比
# TYPE hermes_system_cpu_percent gauge
hermes_system_cpu_percent {cpu_percent}

# HELP hermes_system_memory_percent 内存使用百分比
# TYPE hermes_system_memory_percent gauge
hermes_system_memory_percent {memory.percent}

# HELP hermes_system_memory_bytes 内存使用字节数
# TYPE hermes_system_memory_bytes gauge
hermes_system_memory_bytes {{total="{memory.total}", used="{memory.used}", available="{memory.available}"}}

# HELP hermes_system_disk_percent 磁盘使用百分比
# TYPE hermes_system_disk_percent gauge
hermes_system_disk_percent {disk.percent}

# HELP hermes_system_disk_bytes 磁盘使用字节数
# TYPE hermes_system_disk_bytes gauge
hermes_system_disk_bytes {{total="{disk.total}", used="{disk.used}", available="{disk.available}"}}

# HELP hermes_app_uptime_seconds 应用运行时间（秒）
# TYPE hermes_app_uptime_seconds gauge
hermes_app_uptime_seconds {uptime}

# HELP hermes_app_info 应用信息
# TYPE hermes_app_info gauge
hermes_app_info{{version="1.2.0", environment="production"}} 1
"""

        # 获取业务指标
        from cloud.database.db import db

        # 节点统计
        nodes = db.list_nodes()
        online_nodes = len([n for n in nodes if n.get("status") == "online"])
        total_nodes = len(nodes)

        metrics_text += f"""
# HELP hermes_nodes_total 节点总数
# TYPE hermes_nodes_total gauge
hermes_nodes_total {total_nodes}

# HELP hermes_nodes_online 在线节点数
# TYPE hermes_nodes_online gauge
hermes_nodes_online {online_nodes}
"""

        # 资产统计
        devices = db.list_devices()
        total_devices = len(devices)
        active_devices = len([d for d in devices if d.get("status") == "active"])

        metrics_text += f"""
# HELP hermes_assets_total 资产总数
# TYPE hermes_assets_total gauge
hermes_assets_total {total_devices}

# HELP hermes_assets_active 活跃资产数
# TYPE hermes_assets_active gauge
hermes_assets_active {active_devices}
"""

        # 任务统计
        jobs = db.list_jobs()
        total_jobs = len(jobs)
        running_jobs = len([j for j in jobs if j.get("status") == "running"])
        success_jobs = len([j for j in jobs if j.get("status") == "success"])
        failed_jobs = len([j for j in jobs if j.get("status") == "failed"])

        metrics_text += f"""
# HELP hermes_jobs_total 任务总数
# TYPE hermes_jobs_total gauge
hermes_jobs_total {total_jobs}

# HELP hermes_jobs_running 运行中任务数
# TYPE hermes_jobs_running gauge
hermes_jobs_running {running_jobs}

# HELP hermes_jobs_success 成功任务数
# TYPE hermes_jobs_success gauge
hermes_jobs_success {success_jobs}

# HELP hermes_jobs_failed 失败任务数
# TYPE hermes_jobs_failed gauge
hermes_jobs_failed {failed_jobs}
"""

        return Response(content=metrics_text, media_type="text/plain")

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Metrics collection failed: {str(e)}")


@router.get("/performance")
async def performance_stats():
    """
    性能统计端点

    Returns:
        系统性能统计数据
    """
    try:
        # CPU信息
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # 内存信息
        memory = psutil.virtual_memory()

        # 磁盘I/O信息
        try:
            disk_io = psutil.disk_io_counters()
            disk_stats = {
                "read_bytes": disk_io.read_bytes,
                "write_bytes": disk_io.write_bytes,
                "read_count": disk_io.read_count,
                "write_count": disk_io.write_count
            }
        except:
            disk_stats = {}

        # 网络信息
        try:
            network = psutil.net_io_counters()
            network_stats = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
        except:
            network_stats = {}

        # 进程信息
        process = psutil.Process()
        process_info = {
            "cpu_percent": process.cpu_percent(),
            "memory_info": {
                "rss": process.memory_info().rss,
                "vms": process.memory_info().vms
            },
            "num_threads": process.num_threads(),
            "connections": len(process.connections())
        }

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent
            },
            "disk_io": disk_stats,
            "network": network_stats,
            "process": process_info,
            "uptime": time.time() - _start_time
        }

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Performance stats failed: {str(e)}")


@router.get("/status")
async def system_status():
    """
    系统状态概览

    Returns:
        系统整体状态信息
    """
    try:
        from cloud.database.db import db

        # 获取统计信息
        stats = db.get_stats()

        # 系统资源状态
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=1)

        # 判断系统状态
        system_status = "healthy"
        if cpu_percent > 80 or memory.percent > 85 or disk.percent > 90:
            system_status = "warning"
        if cpu_percent > 95 or memory.percent > 95 or disk.percent > 95:
            system_status = "critical"

        return {
            "status": system_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "uptime_hours": (time.time() - _start_time) / 3600
            },
            "business": {
                "total_nodes": stats.get("total_nodes", 0),
                "total_devices": stats.get("total_devices", 0),
                "total_jobs": stats.get("total_jobs", 0),
                "active_nodes": stats.get("active_nodes", 0),
                "running_jobs": stats.get("running_jobs", 0)
            },
            "version": "1.2.0"
        }

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"System status failed: {str(e)}")