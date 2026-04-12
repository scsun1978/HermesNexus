"""
SQLite数据库持久化实现

提供基于SQLite的数据库持久化功能，支持数据重启恢复
"""

import sqlite3
import threading
import json
import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class SQLiteDatabase:
    """SQLite数据库实现（线程安全）"""

    def __init__(self, db_path: str = "hermesnexus.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()

    def _init_database(self):
        """初始化数据库表结构"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")

                # 创建节点表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS nodes (
                        node_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        capabilities TEXT,
                        last_heartbeat TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        tags TEXT,
                        cpu_usage REAL DEFAULT 0.0,
                        memory_usage REAL DEFAULT 0.0,
                        active_tasks INTEGER DEFAULT 0
                    )
                """)

                # 创建设备表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS devices (
                        id TEXT PRIMARY KEY,
                        device_id TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        protocol TEXT NOT NULL,
                        host TEXT NOT NULL,
                        port INTEGER NOT NULL,
                        credentials TEXT,
                        status TEXT DEFAULT 'unknown',
                        node_id TEXT,
                        tags TEXT,
                        metadata TEXT,
                        last_seen TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        enabled INTEGER DEFAULT 1
                    )
                """)

                # 创建任务表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS jobs (
                        job_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        target_device_id TEXT,
                        target_device_name TEXT,
                        task_type TEXT,
                        command TEXT,
                        script TEXT,
                        parameters TEXT,
                        priority TEXT DEFAULT 'normal',
                        timeout INTEGER DEFAULT 300,
                        node_id TEXT,
                        target_host TEXT,
                        created_by TEXT DEFAULT 'user',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        result TEXT,
                        completed_at TEXT,
                        error_message TEXT,
                        error_code TEXT
                    )
                """)

                # 创建事件表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        event_id TEXT PRIMARY KEY,
                        type TEXT NOT NULL,
                        level TEXT NOT NULL,
                        source TEXT,
                        source_type TEXT,
                        title TEXT,
                        message TEXT NOT NULL,
                        related_job_id TEXT,
                        related_node_id TEXT,
                        related_device_id TEXT,
                        data TEXT,
                        timestamp TEXT NOT NULL
                    )
                """)

                # 创建审计日志表
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        log_id TEXT PRIMARY KEY,
                        action TEXT NOT NULL,
                        actor TEXT,
                        target_type TEXT,
                        target_id TEXT,
                        details TEXT,
                        ip_address TEXT,
                        user_agent TEXT,
                        timestamp TEXT NOT NULL
                    )
                """)

                # 创建索引
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_nodes_status ON nodes(status)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_events_type ON events(type)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)"
                )

                conn.commit()
                logger.info(f"✅ SQLite数据库初始化完成: {self.db_path}")

        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            raise

    # 节点操作
    def add_node(self, node_id: str, node_data: Dict) -> bool:
        """添加节点"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO nodes
                        (node_id, name, status, capabilities, last_heartbeat,
                         created_at, updated_at, tags, cpu_usage, memory_usage, active_tasks)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            node_id,
                            node_data.get("name"),
                            node_data.get("status", "offline"),
                            json.dumps(node_data.get("capabilities", {})),
                            node_data.get("last_heartbeat"),
                            node_data.get(
                                "created_at", datetime.now(timezone.utc).isoformat()
                            ),
                            node_data.get(
                                "updated_at", datetime.now(timezone.utc).isoformat()
                            ),
                            json.dumps(node_data.get("tags", [])),
                            node_data.get("cpu_usage", 0.0),
                            node_data.get("memory_usage", 0.0),
                            node_data.get("active_tasks", 0),
                        ),
                    )
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"❌ 添加节点失败: {e}")
            return False

    def get_node(self, node_id: str) -> Optional[Dict]:
        """获取节点"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM nodes WHERE node_id = ?", (node_id,)
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_dict(row)
                return None
        except Exception as e:
            logger.error(f"❌ 获取节点失败: {e}")
            return None

    def update_node(self, node_id: str, updates: Dict) -> bool:
        """更新节点"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    update_fields = []
                    update_values = []

                    for key, value in updates.items():
                        if key in ["capabilities", "tags"]:
                            update_fields.append(f"{key} = ?")
                            update_values.append(json.dumps(value))
                        elif key in ["cpu_usage", "memory_usage", "active_tasks"]:
                            update_fields.append(f"{key} = ?")
                            update_values.append(value)
                        else:
                            update_fields.append(f"{key} = ?")
                            update_values.append(value)

                    update_fields.append("updated_at = ?")
                    update_values.append(datetime.now(timezone.utc).isoformat())
                    update_values.append(node_id)

                    sql = (
                        f"UPDATE nodes SET {', '.join(update_fields)} WHERE node_id = ?"
                    )
                    conn.execute(sql, update_values)
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"❌ 更新节点失败: {e}")
            return False

    def list_nodes(self, status: Optional[str] = None) -> List[Dict]:
        """列出节点"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                if status:
                    cursor = conn.execute(
                        "SELECT * FROM nodes WHERE status = ?", (status,)
                    )
                else:
                    cursor = conn.execute("SELECT * FROM nodes")

                return [self._row_to_dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ 列出节点失败: {e}")
            return []

    # 设备操作
    def add_device(self, device_id: str, device_data: Dict) -> bool:
        """添加设备"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO devices
                        (id, device_id, name, type, protocol, host, port,
                         credentials, status, node_id, tags, metadata,
                         last_seen, created_at, updated_at, enabled)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            device_data.get("id"),
                            device_id,
                            device_data.get("name"),
                            device_data.get("type"),
                            device_data.get("protocol"),
                            device_data.get("host"),
                            device_data.get("port"),
                            json.dumps(device_data.get("credentials", {})),
                            device_data.get("status", "unknown"),
                            device_data.get("node_id"),
                            json.dumps(device_data.get("tags", [])),
                            json.dumps(device_data.get("metadata", {})),
                            device_data.get("last_seen"),
                            device_data.get(
                                "created_at", datetime.now(timezone.utc).isoformat()
                            ),
                            device_data.get(
                                "updated_at", datetime.now(timezone.utc).isoformat()
                            ),
                            1 if device_data.get("enabled", True) else 0,
                        ),
                    )
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"❌ 添加设备失败: {e}")
            return False

    def get_device(self, device_id: str) -> Optional[Dict]:
        """获取设备"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM devices WHERE device_id = ?", (device_id,)
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_dict(row)
                return None
        except Exception as e:
            logger.error(f"❌ 获取设备失败: {e}")
            return None

    def list_devices(self) -> List[Dict]:
        """列出设备"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM devices")
                return [self._row_to_dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ 列出设备失败: {e}")
            return []

    # 任务操作
    def add_job(self, job_id: str, job_data: Dict) -> bool:
        """添加任务"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO jobs
                        (job_id, name, type, status, target_device_id, target_device_name,
                         task_type, command, script, parameters, priority, timeout,
                         node_id, target_host, created_by, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            job_id,
                            job_data.get("name"),
                            job_data.get("type"),
                            job_data.get("status", "pending"),
                            job_data.get("target_device_id"),
                            job_data.get("target_device_name"),
                            job_data.get("task_type"),
                            job_data.get("command"),
                            job_data.get("script"),
                            json.dumps(job_data.get("parameters", {})),
                            job_data.get("priority", "normal"),
                            job_data.get("timeout", 300),
                            job_data.get("node_id"),
                            job_data.get("target_host"),
                            job_data.get("created_by", "user"),
                            job_data.get(
                                "created_at", datetime.now(timezone.utc).isoformat()
                            ),
                            job_data.get(
                                "updated_at", datetime.now(timezone.utc).isoformat()
                            ),
                        ),
                    )
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"❌ 添加任务失败: {e}")
            return False

    def get_job(self, job_id: str) -> Optional[Dict]:
        """获取任务"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_dict(row)
                return None
        except Exception as e:
            logger.error(f"❌ 获取任务失败: {e}")
            return None

    def update_job(self, job_id: str, updates: Dict) -> bool:
        """更新任务"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    update_fields = []
                    update_values = []

                    for key, value in updates.items():
                        if key in ["parameters", "result"]:
                            update_fields.append(f"{key} = ?")
                            update_values.append(json.dumps(value))
                        else:
                            update_fields.append(f"{key} = ?")
                            update_values.append(value)

                    update_fields.append("updated_at = ?")
                    update_values.append(datetime.now(timezone.utc).isoformat())
                    update_values.append(job_id)

                    sql = f"UPDATE jobs SET {', '.join(update_fields)} WHERE job_id = ?"
                    conn.execute(sql, update_values)
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"❌ 更新任务失败: {e}")
            return False

    def list_jobs(
        self, status: Optional[str] = None, node_id: Optional[str] = None
    ) -> List[Dict]:
        """列出任务"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                sql = "SELECT * FROM jobs WHERE 1=1"
                params = []

                if status:
                    sql += " AND status = ?"
                    params.append(status)

                if node_id:
                    sql += " AND node_id = ?"
                    params.append(node_id)

                sql += " ORDER BY created_at DESC"

                cursor = conn.execute(sql, params)
                return [self._row_to_dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ 列出任务失败: {e}")
            return []

    # 事件操作
    def add_event(self, event_data: Dict) -> bool:
        """添加事件"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    event_id = event_data.get("event_id")
                    if not event_id:
                        return False

                    conn.execute(
                        """
                        INSERT INTO events
                        (event_id, type, level, source, source_type, title, message,
                         related_job_id, related_node_id, related_device_id, data, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            event_id,
                            event_data.get("type"),
                            event_data.get("level", "info"),
                            event_data.get("source"),
                            event_data.get("source_type"),
                            event_data.get("title"),
                            event_data.get("message"),
                            event_data.get("related_job_id"),
                            event_data.get("related_node_id"),
                            event_data.get("related_device_id"),
                            json.dumps(event_data.get("data", {})),
                            event_data.get(
                                "timestamp", datetime.now(timezone.utc).isoformat()
                            ),
                        ),
                    )
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"❌ 添加事件失败: {e}")
            return False

    def list_events(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """列出事件"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM events ORDER BY timestamp ASC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
                return [self._row_to_dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ 列出事件失败: {e}")
            return []

    # 审计日志操作
    def add_audit_log(self, log_data: Dict) -> bool:
        """添加审计日志"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    # 如果没有提供log_id，自动生成一个
                    log_id = (
                        log_data.get("log_id")
                        or f"audit-{int(datetime.now(timezone.utc).timestamp())}-{str(uuid.uuid4())[:8]}"
                    )

                    conn.execute(
                        """
                        INSERT INTO audit_logs
                        (log_id, action, actor, target_type, target_id, details,
                         ip_address, user_agent, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            log_id,
                            log_data.get("action"),
                            log_data.get("actor"),
                            log_data.get("target_type"),
                            log_data.get("target_id"),
                            json.dumps(log_data.get("details", {})),
                            log_data.get("ip_address"),
                            log_data.get("user_agent"),
                            log_data.get(
                                "timestamp", datetime.now(timezone.utc).isoformat()
                            ),
                        ),
                    )
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"❌ 添加审计日志失败: {e}")
            return False

    def list_audit_logs(self, limit: int = 100) -> List[Dict]:
        """列出审计日志"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
                )
                return [self._row_to_dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ 列出审计日志失败: {e}")
            return []

    # 统计信息
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {}

                # 节点统计
                cursor = conn.execute("SELECT COUNT(*) FROM nodes")
                stats["total_nodes"] = cursor.fetchone()[0]

                cursor = conn.execute(
                    "SELECT COUNT(*) FROM nodes WHERE status = 'online'"
                )
                stats["online_nodes"] = cursor.fetchone()[0]

                # 设备统计
                cursor = conn.execute("SELECT COUNT(*) FROM devices")
                stats["total_devices"] = cursor.fetchone()[0]

                # 任务统计
                cursor = conn.execute("SELECT COUNT(*) FROM jobs")
                stats["total_jobs"] = cursor.fetchone()[0]

                cursor = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE status = 'pending'"
                )
                stats["pending_jobs"] = cursor.fetchone()[0]

                cursor = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE status = 'running'"
                )
                stats["running_jobs"] = cursor.fetchone()[0]

                cursor = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE status = 'completed'"
                )
                stats["completed_jobs"] = cursor.fetchone()[0]

                # 事件统计
                cursor = conn.execute("SELECT COUNT(*) FROM events")
                stats["total_events"] = cursor.fetchone()[0]

                # 审计日志统计
                cursor = conn.execute("SELECT COUNT(*) FROM audit_logs")
                stats["total_audit_logs"] = cursor.fetchone()[0]

                return stats
        except Exception as e:
            logger.error(f"❌ 获取统计信息失败: {e}")
            return {}

    # 工具方法
    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """将数据库行转换为字典"""
        result = {}
        for key in row.keys():
            value = row[key]
            # 处理JSON字段
            if key in [
                "capabilities",
                "tags",
                "credentials",
                "metadata",
                "parameters",
                "result",
                "data",
                "details",
            ]:
                try:
                    if value:
                        result[key] = json.loads(value)
                    else:
                        result[key] = {}
                except:
                    result[key] = value
            # 处理布尔字段
            elif key == "enabled":
                result[key] = bool(value)
            else:
                result[key] = value
        return result

    def backup(self, backup_path: str) -> bool:
        """备份数据库"""
        try:
            import shutil

            shutil.copy2(self.db_path, backup_path)
            logger.info(f"✅ 数据库备份成功: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 数据库备份失败: {e}")
            return False

    def restore(self, backup_path: str) -> bool:
        """恢复数据库"""
        try:
            import shutil

            shutil.copy2(backup_path, self.db_path)
            logger.info(f"✅ 数据库恢复成功: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 数据库恢复失败: {e}")
            return False
