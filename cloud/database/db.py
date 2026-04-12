"""
数据库操作工具类

提供线程安全的数据库访问
"""

import threading
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class Database:
    """内存数据库（线程安全）"""

    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.devices: Dict[str, Dict] = {}
        self.jobs: Dict[str, Dict] = {}
        self.events: List[Dict] = []
        self.audit_logs: List[Dict] = []
        self.lock = threading.Lock()

    # 节点操作
    def add_node(self, node_id: str, node_data: Dict) -> bool:
        with self.lock:
            self.nodes[node_id] = {
                **node_data,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            return True

    def get_node(self, node_id: str) -> Optional[Dict]:
        with self.lock:
            return self.nodes.get(node_id)

    def update_node(self, node_id: str, updates: Dict) -> bool:
        with self.lock:
            if node_id in self.nodes:
                self.nodes[node_id].update(updates)
                self.nodes[node_id]["updated_at"] = datetime.now(
                    timezone.utc
                ).isoformat()
                return True
            return False

    def list_nodes(self, status: Optional[str] = None) -> List[Dict]:
        with self.lock:
            nodes = list(self.nodes.values())
            if status:
                return [node for node in nodes if node.get("status") == status]
            return nodes

    # 设备操作
    def add_device(self, device_id: str, device_data: Dict) -> bool:
        with self.lock:
            self.devices[device_id] = {
                **device_data,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            return True

    def get_device(self, device_id: str) -> Optional[Dict]:
        with self.lock:
            return self.devices.get(device_id)

    def update_device(self, device_id: str, updates: Dict) -> bool:
        with self.lock:
            if device_id in self.devices:
                self.devices[device_id].update(updates)
                self.devices[device_id]["updated_at"] = datetime.now(
                    timezone.utc
                ).isoformat()
                return True
            return False

    def list_devices(self) -> List[Dict]:
        with self.lock:
            return list(self.devices.values())

    # 任务操作
    def add_job(self, job_id: str, job_data: Dict) -> bool:
        with self.lock:
            self.jobs[job_id] = {
                **job_data,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending",
            }
            return True

    def get_job(self, job_id: str) -> Optional[Dict]:
        with self.lock:
            return self.jobs.get(job_id)

    def update_job(self, job_id: str, updates: Dict) -> bool:
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].update(updates)
                self.jobs[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
                return True
            return False

    def list_jobs(
        self, status: Optional[str] = None, node_id: Optional[str] = None
    ) -> List[Dict]:
        with self.lock:
            jobs = list(self.jobs.values())

            if status:
                jobs = [j for j in jobs if j.get("status") == status]
            if node_id:
                jobs = [j for j in jobs if j.get("node_id") == node_id]

            return jobs

    # 事件操作
    def add_event(self, event_data: Dict) -> bool:
        with self.lock:
            event = {**event_data, "timestamp": datetime.now(timezone.utc).isoformat()}
            self.events.append(event)

            # 保持最多1000个事件
            if len(self.events) > 1000:
                self.events = self.events[-1000:]

            return True

    def list_events(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[Dict]:
        with self.lock:
            events = list(self.events)  # 按写入顺序返回

            if event_type:
                events = [e for e in events if e.get("type") == event_type]
            if source:
                events = [e for e in events if e.get("source") == source]

            return events[:limit]

    # 审计日志操作
    def add_audit_log(self, audit_data: Dict) -> bool:
        with self.lock:
            audit = {**audit_data, "timestamp": datetime.now(timezone.utc).isoformat()}
            self.audit_logs.append(audit)

            # 保持最多1000个审计日志
            if len(self.audit_logs) > 1000:
                self.audit_logs = self.audit_logs[-1000:]

            return True

    def list_audit_logs(
        self,
        limit: int = 100,
        action: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> List[Dict]:
        with self.lock:
            logs = list(reversed(self.audit_logs))  # 最新的在前

            if action:
                logs = [l for l in logs if l.get("action") == action]
            if actor:
                logs = [l for l in logs if l.get("actor") == actor]

            return logs[:limit]

    # 统计信息
    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "total_nodes": len(self.nodes),
                "online_nodes": len(
                    [n for n in self.nodes.values() if n.get("status") == "online"]
                ),
                "total_devices": len(self.devices),
                "total_jobs": len(self.jobs),
                "pending_jobs": len(
                    [j for j in self.jobs.values() if j.get("status") == "pending"]
                ),
                "running_jobs": len(
                    [j for j in self.jobs.values() if j.get("status") == "running"]
                ),
                "completed_jobs": len(
                    [
                        j
                        for j in self.jobs.values()
                        if j.get("status") in ["success", "failed"]
                    ]
                ),
                "total_events": len(self.events),
                "total_audit_logs": len(self.audit_logs),
            }


# 全局数据库实例 - 根据环境变量选择数据库类型
def _create_database_instance():
    """根据配置创建数据库实例"""
    db_type = os.getenv("DB_TYPE", "memory").lower()

    if db_type == "sqlite":
        # 使用SQLite持久化数据库
        from cloud.database.sqlite_db import SQLiteDatabase

        db_path = os.getenv("SQLITE_DB_PATH", "./data/hermesnexus.db")
        # 确保数据目录存在
        data_dir = os.path.dirname(db_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
        logger.info(f"🗄️  使用SQLite数据库: {db_path}")
        return SQLiteDatabase(db_path)
    else:
        # 默认使用内存数据库
        logger.info("💾 使用内存数据库")
        return Database()


db = _create_database_instance()
