#!/usr/bin/env python3
"""
HermesNexus v1.2.0 Cloud API (标准库版本)
基于Python标准库实现，无需外部依赖
包含v1.2.0的核心监控和管理功能
"""

import http.server
import socketserver
import json
import sqlite3
import os
import urllib.parse
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
import socket
import subprocess
import uuid

class HermesNexusCloudAPI:
    """HermesNexus Cloud API v1.2.0"""

    def __init__(self, host='0.0.0.0', port=8082):
        self.host = host
        self.port = port
        self.version = "1.2.0"
        self.start_time = time.time()

        # 数据库路径 - 使用固定路径确保权限正确
        self.db_path = '/home/scsun/hermesnexus-data/hermesnexus-v12.db'

        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # 初始化数据库
        self.init_database()

        # 内存存储
        self.nodes = {}
        self.assets = {}
        self.jobs = {}
        self.audit_logs = []

    def init_database(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建节点表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT,
                hostname TEXT,
                ip_address TEXT,
                port INTEGER,
                status TEXT,
                last_heartbeat TEXT,
                capabilities TEXT,
                metadata TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')

        # 创建资产表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assets (
                asset_id TEXT PRIMARY KEY,
                name TEXT,
                asset_type TEXT,
                status TEXT,
                hostname TEXT,
                ip_address TEXT,
                node_id TEXT,
                metadata TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')

        # 创建任务表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                name TEXT,
                job_type TEXT,
                status TEXT,
                target_node_id TEXT,
                command TEXT,
                result TEXT,
                created_by TEXT,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT
            )
        ''')

        # 创建审计日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id TEXT PRIMARY KEY,
                timestamp TEXT,
                actor TEXT,
                action TEXT,
                target_type TEXT,
                target_id TEXT,
                details TEXT,
                level TEXT
            )
        ''')

        # 创建系统指标表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                metric_type TEXT,
                metric_name TEXT,
                metric_value REAL,
                labels TEXT
            )
        ''')

        conn.commit()
        conn.close()

        print(f"✅ 数据库初始化完成: {self.db_path}")

    def log_audit(self, actor, action, target_type=None, target_id=None, details=None, level="INFO"):
        """记录审计日志"""
        log_entry = {
            "log_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "details": details or {},
            "level": level
        }

        # 保存到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audit_logs (log_id, timestamp, actor, action, target_type, target_id, details, level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            log_entry["log_id"], log_entry["timestamp"], log_entry["actor"],
            log_entry["action"], log_entry["target_type"], log_entry["target_id"],
            json.dumps(log_entry["details"]), log_entry["level"]
        ))
        conn.commit()
        conn.close()

        # 同时保存到内存
        self.audit_logs.append(log_entry)

        return log_entry

    def get_system_metrics(self):
        """获取系统指标"""
        try:
            # CPU使用率
            with open('/proc/loadavg', 'r') as f:
                load_avg = f.read().split()[0]
                cpu_percent = float(load_avg) * 100

            # 内存使用率
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
                mem_total = int([line for line in meminfo.split('\n') if 'MemTotal' in line][0].split()[1])
                mem_free = int([line for line in meminfo.split('\n') if 'MemFree' in line][0].split()[1])
                memory_percent = ((mem_total - mem_free) / mem_total) * 100

            # 磁盘使用率
            stat = os.statvfs('/')
            disk_total = stat.f_blocks * stat.f_frsize
            disk_free = stat.f_bavail * stat.f_frsize
            disk_percent = ((disk_total - disk_free) / disk_total) * 100

            return {
                "cpu_percent": min(cpu_percent, 100),
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "uptime_seconds": time.time() - self.start_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "disk_percent": 0,
                "uptime_seconds": time.time() - self.start_time,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }

    def get_business_metrics(self):
        """获取业务指标"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 节点统计
        cursor.execute('SELECT status, COUNT(*) FROM nodes GROUP BY status')
        node_stats = dict(cursor.fetchall())
        total_nodes = sum(node_stats.values())
        online_nodes = node_stats.get('online', 0)

        # 资产统计
        cursor.execute('SELECT status, COUNT(*) FROM assets GROUP BY status')
        asset_stats = dict(cursor.fetchall())
        total_assets = sum(asset_stats.values())

        # 任务统计
        cursor.execute('SELECT status, COUNT(*) FROM jobs GROUP BY status')
        job_stats = dict(cursor.fetchall())
        total_jobs = sum(job_stats.values())
        running_jobs = job_stats.get('running', 0)

        conn.close()

        return {
            "nodes": {
                "total": total_nodes,
                "online": online_nodes,
                "offline": total_nodes - online_nodes
            },
            "assets": {
                "total": total_assets,
                "active": asset_stats.get('active', 0)
            },
            "jobs": {
                "total": total_jobs,
                "running": running_jobs,
                "completed": job_stats.get('completed', 0),
                "failed": job_stats.get('failed', 0)
            }
        }

    def generate_prometheus_metrics(self):
        """生成Prometheus格式的监控指标"""
        system_metrics = self.get_system_metrics()
        business_metrics = self.get_business_metrics()

        metrics_text = f"""# HELP hermes_system_cpu_percent CPU使用百分比
# TYPE hermes_system_cpu_percent gauge
hermes_system_cpu_percent {system_metrics['cpu_percent']}

# HELP hermes_system_memory_percent 内存使用百分比
# TYPE hermes_system_memory_percent gauge
hermes_system_memory_percent {system_metrics['memory_percent']}

# HELP hermes_system_disk_percent 磁盘使用百分比
# TYPE hermes_system_disk_percent gauge
hermes_system_disk_percent {system_metrics['disk_percent']}

# HELP hermes_app_uptime_seconds 应用运行时间（秒）
# TYPE hermes_app_uptime_seconds gauge
hermes_app_uptime_seconds {system_metrics['uptime_seconds']}

# HELP hermes_app_info 应用信息
# TYPE hermes_app_info gauge
hermes_app_info{{version="{self.version}", environment="production"}} 1

# HELP hermes_nodes_total 节点总数
# TYPE hermes_nodes_total gauge
hermes_nodes_total {business_metrics['nodes']['total']}

# HELP hermes_nodes_online 在线节点数
# TYPE hermes_nodes_online gauge
hermes_nodes_online {business_metrics['nodes']['online']}

# HELP hermes_assets_total 资产总数
# TYPE hermes_assets_total gauge
hermes_assets_total {business_metrics['assets']['total']}

# HELP hermes_jobs_total 任务总数
# TYPE hermes_jobs_total gauge
hermes_jobs_total {business_metrics['jobs']['total']}

# HELP hermes_jobs_running 运行中任务数
# TYPE hermes_jobs_running gauge
hermes_jobs_running {business_metrics['jobs']['running']}
"""

        return metrics_text

class HermesAPIRequestHandler(http.server.BaseHTTPRequestHandler):
    """HermesNexus API请求处理器"""

    def __init__(self, *args, server=None, **kwargs):
        self.server_instance = server
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """处理GET请求"""
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path
            query_params = urllib.parse.parse_qs(parsed_path.query)

            # 健康检查
            if path == '/health' or path == '/api/health':
                self.send_json_response({
                    "status": "healthy",
                    "version": self.server_instance.version,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "uptime_seconds": time.time() - self.server_instance.start_time
                })

            # 监控健康检查
            elif path == '/monitoring/health':
                system_metrics = self.server_instance.get_system_metrics()

                # 确定整体健康状态
                overall_health = "healthy"
                if system_metrics['cpu_percent'] > 80 or system_metrics['memory_percent'] > 85 or system_metrics['disk_percent'] > 90:
                    overall_health = "warning"
                if system_metrics['cpu_percent'] > 95 or system_metrics['memory_percent'] > 95 or system_metrics['disk_percent'] > 95:
                    overall_health = "critical"

                self.send_json_response({
                    "status": overall_health,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "uptime_seconds": time.time() - self.server_instance.start_time,
                    "system": system_metrics,
                    "business": self.server_instance.get_business_metrics(),
                    "version": self.server_instance.version
                })

            # Prometheus指标
            elif path == '/monitoring/metrics':
                prometheus_text = self.server_instance.generate_prometheus_metrics()
                self.send_text_response(prometheus_text, content_type='text/plain')

            # 性能统计
            elif path == '/monitoring/performance':
                system_metrics = self.server_instance.get_system_metrics()

                self.send_json_response({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "system": system_metrics,
                    "business": self.server_instance.get_business_metrics(),
                    "performance": {
                        "request_count": getattr(self.server_instance, 'request_count', 0),
                        "avg_response_time": getattr(self.server_instance, 'avg_response_time', 0.001)
                    }
                })

            # 系统状态
            elif path == '/monitoring/status':
                system_metrics = self.server_instance.get_system_metrics()
                business_metrics = self.server_instance.get_business_metrics()

                system_status = "healthy"
                if system_metrics['cpu_percent'] > 80 or system_metrics['memory_percent'] > 85 or system_metrics['disk_percent'] > 90:
                    system_status = "warning"
                if system_metrics['cpu_percent'] > 95 or system_metrics['memory_percent'] > 95 or system_metrics['disk_percent'] > 95:
                    system_status = "critical"

                self.send_json_response({
                    "status": system_status,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "system": system_metrics,
                    "business": business_metrics,
                    "version": self.server_instance.version
                })

            # 节点列表
            elif path == '/api/nodes':
                conn = sqlite3.connect(self.server_instance.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM nodes')
                nodes = []
                for row in cursor.fetchall():
                    nodes.append({
                        "node_id": row[0],
                        "node_type": row[1],
                        "hostname": row[2],
                        "ip_address": row[3],
                        "port": row[4],
                        "status": row[5],
                        "last_heartbeat": row[6],
                        "capabilities": json.loads(row[7]) if row[7] else {},
                        "metadata": json.loads(row[8]) if row[8] else {},
                        "created_at": row[9],
                        "updated_at": row[10]
                    })
                conn.close()

                self.send_json_response({
                    "nodes": nodes,
                    "total": len(nodes),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            # 资产列表
            elif path == '/api/assets':
                conn = sqlite3.connect(self.server_instance.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM assets')
                assets = []
                for row in cursor.fetchall():
                    assets.append({
                        "asset_id": row[0],
                        "name": row[1],
                        "asset_type": row[2],
                        "status": row[3],
                        "hostname": row[4],
                        "ip_address": row[5],
                        "node_id": row[6],
                        "metadata": json.loads(row[7]) if row[7] else {},
                        "created_at": row[8],
                        "updated_at": row[9]
                    })
                conn.close()

                self.send_json_response({
                    "assets": assets,
                    "total": len(assets),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            # 任务列表
            elif path == '/api/jobs':
                conn = sqlite3.connect(self.server_instance.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100')
                jobs = []
                for row in cursor.fetchall():
                    jobs.append({
                        "job_id": row[0],
                        "name": row[1],
                        "job_type": row[2],
                        "status": row[3],
                        "target_node_id": row[4],
                        "command": row[5],
                        "result": json.loads(row[6]) if row[6] else None,
                        "created_by": row[7],
                        "created_at": row[8],
                        "started_at": row[9],
                        "completed_at": row[10]
                    })
                conn.close()

                self.send_json_response({
                    "jobs": jobs,
                    "total": len(jobs),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            # 单个任务详情
            elif path.startswith('/api/jobs/') and path.count('/') == 3:
                job_id = path.split('/')[-1]
                conn = sqlite3.connect(self.server_instance.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id,))
                row = cursor.fetchone()
                conn.close()

                if row:
                    self.send_json_response({
                        "job_id": row[0],
                        "name": row[1],
                        "job_type": row[2],
                        "status": row[3],
                        "target_node_id": row[4],
                        "command": row[5],
                        "result": json.loads(row[6]) if row[6] else None,
                        "created_by": row[7],
                        "created_at": row[8],
                        "started_at": row[9],
                        "completed_at": row[10],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                else:
                    self.send_json_response({
                        "error": "Job not found",
                        "job_id": job_id
                    }, status=404)

            # API根路径
            elif path == '/api' or path == '/':
                self.send_json_response({
                    "name": "HermesNexus Cloud API",
                    "version": self.server_instance.version,
                    "status": "running",
                    "endpoints": [
                        "/health",
                        "/monitoring/health",
                        "/monitoring/metrics",
                        "/monitoring/performance",
                        "/monitoring/status",
                        "/api/nodes",
                        "/api/assets",
                        "/api/jobs",
                        "/api/v1/tasks",
                        "/api/v1/nodes"
                    ],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            # API v1 兼容层 - /api/v1/tasks
            elif path == '/api/v1/tasks':
                # 重定向到任务列表
                conn = sqlite3.connect(self.server_instance.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100')
                jobs = []
                for row in cursor.fetchall():
                    jobs.append({
                        "job_id": row[0],
                        "name": row[1],
                        "job_type": row[2],
                        "status": row[3],
                        "target_node_id": row[4],
                        "command": row[5],
                        "result": json.loads(row[6]) if row[6] else None,
                        "created_by": row[7],
                        "created_at": row[8],
                        "started_at": row[9],
                        "completed_at": row[10]
                    })
                conn.close()

                self.send_json_response({
                    "tasks": jobs,
                    "total": len(jobs),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            # API v1 兼容层 - /api/v1/nodes/<id>/heartbeat
            elif '/api/v1/nodes/' in path and '/heartbeat' in path:
                # 从路径中提取node_id
                parts = path.split('/')
                node_id = parts[4]  # /api/v1/nodes/<node_id>/heartbeat

                # 复用现有的心跳逻辑
                heartbeat_data = {
                    "node_id": node_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "online",
                    "system_info": self.server_instance.get_system_metrics()
                }

                # 更新数据库
                conn = sqlite3.connect(self.server_instance.db_path)
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE nodes SET
                        last_heartbeat = ?,
                        status = 'online',
                        updated_at = ?
                    WHERE node_id = ?
                ''', (
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    node_id
                ))

                conn.commit()
                conn.close()

                self.send_json_response({
                    "status": "success",
                    "message": "Heartbeat received",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            # API v1 兼容层 - /api/v1/nodes/<id>/tasks/<task_id>/result
            elif '/api/v1/nodes/' in path and '/tasks/' in path and '/result' in path:
                # 从路径中提取node_id和task_id
                parts = path.split('/')
                node_id = parts[4]
                task_id = parts[6]

                # 从数据库获取任务结果
                conn = sqlite3.connect(self.server_instance.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM jobs WHERE job_id = ?', (task_id,))
                row = cursor.fetchone()
                conn.close()

                if row and row[3] in ['completed', 'failed']:
                    self.send_json_response({
                        "node_id": node_id,
                        "task_id": task_id,
                        "result": json.loads(row[6]) if row[6] else None,
                        "status": row[3],
                        "completed_at": row[10],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                else:
                    self.send_json_response({
                        "error": "Task not found or not completed",
                        "task_id": task_id,
                        "status": row[3] if row else "unknown"
                    }, status=404)

            else:
                self.send_json_response({
                    "error": "Not Found",
                    "path": path,
                    "message": "The requested endpoint does not exist"
                }, status=404)

        except Exception as e:
            self.send_json_response({
                "error": "Internal Server Error",
                "message": str(e),
                "traceback": traceback.format_exc()
            }, status=500)

    def do_POST(self):
        """处理POST请求"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8')) if post_data else {}

            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path

            # 节点注册
            if path == '/api/nodes/register':
                node_data = body
                node_id = node_data.get('node_id', str(uuid.uuid4()))

                conn = sqlite3.connect(self.server_instance.db_path)
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT OR REPLACE INTO nodes
                    (node_id, node_type, hostname, ip_address, port, status, last_heartbeat, capabilities, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    node_id,
                    node_data.get('node_type', 'edge'),
                    node_data.get('hostname', ''),
                    node_data.get('ip_address', ''),
                    node_data.get('port', 8081),
                    node_data.get('status', 'online'),
                    datetime.now(timezone.utc).isoformat(),
                    json.dumps(node_data.get('capabilities', {})),
                    json.dumps(node_data.get('metadata', {})),
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat()
                ))

                conn.commit()
                conn.close()

                # 记录审计日志
                self.server_instance.log_audit(
                    actor=node_id,
                    action="node_registered",
                    target_type="node",
                    target_id=node_id,
                    details=node_data
                )

                self.send_json_response({
                    "status": "success",
                    "message": "Node registered successfully",
                    "node_id": node_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            # 心跳
            elif path == '/api/nodes/heartbeat':
                node_id = body.get('node_id')
                if not node_id:
                    self.send_json_response({
                        "error": "Missing node_id"
                    }, status=400)
                    return

                conn = sqlite3.connect(self.server_instance.db_path)
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE nodes SET
                        last_heartbeat = ?,
                        status = 'online',
                        updated_at = ?
                    WHERE node_id = ?
                ''', (
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    node_id
                ))

                conn.commit()
                conn.close()

                self.send_json_response({
                    "status": "success",
                    "message": "Heartbeat received",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            # 创建任务
            elif path == '/api/jobs':
                job_data = body
                job_id = job_data.get('job_id', str(uuid.uuid4()))

                conn = sqlite3.connect(self.server_instance.db_path)
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO jobs
                    (job_id, name, job_type, status, target_node_id, command, result, created_by, created_at, started_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    job_id,
                    job_data.get('name', 'Unnamed Job'),
                    job_data.get('job_type', 'command'),
                    'pending',
                    job_data.get('target_node_id', ''),
                    job_data.get('command', ''),
                    None,
                    job_data.get('created_by', 'system'),
                    datetime.now(timezone.utc).isoformat(),
                    None,
                    None
                ))

                conn.commit()
                conn.close()

                # 记录审计日志
                self.server_instance.log_audit(
                    actor=job_data.get('created_by', 'system'),
                    action="job_created",
                    target_type="job",
                    target_id=job_id,
                    details=job_data
                )

                self.send_json_response({
                    "status": "success",
                    "message": "Job created successfully",
                    "job_id": job_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            else:
                self.send_json_response({
                    "error": "Not Found",
                    "path": path,
                    "message": "The requested endpoint does not exist"
                }, status=404)

        except json.JSONDecodeError:
            self.send_json_response({
                "error": "Invalid JSON",
                "message": "Request body contains invalid JSON"
            }, status=400)
        except Exception as e:
            self.send_json_response({
                "error": "Internal Server Error",
                "message": str(e),
                "traceback": traceback.format_exc()
            }, status=500)

    def do_PATCH(self):
        """处理PATCH请求 - 用于更新任务状态"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8')) if post_data else {}

            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path

            # 更新任务状态和结果
            if path.startswith('/api/jobs/') and path.endswith('/status'):
                job_id = path.split('/')[-2]
                status_update = body

                conn = sqlite3.connect(self.server_instance.db_path)
                cursor = conn.cursor()

                # 更新任务状态
                update_fields = []
                update_values = []

                if 'status' in status_update:
                    update_fields.append('status = ?')
                    update_values.append(status_update['status'])

                if 'result' in status_update:
                    update_fields.append('result = ?')
                    update_values.append(json.dumps(status_update['result']))

                if 'started_at' in status_update:
                    update_fields.append('started_at = ?')
                    update_values.append(status_update['started_at'])

                if 'completed_at' in status_update:
                    update_fields.append('completed_at = ?')
                    update_values.append(status_update['completed_at'])

                if update_fields:
                    update_values.append(job_id)
                    update_query = f"UPDATE jobs SET {', '.join(update_fields)} WHERE job_id = ?"
                    cursor.execute(update_query, update_values)
                    conn.commit()

                    # 记录审计日志
                    self.server_instance.log_audit(
                        actor=f"node_{job_id}",
                        action="job_status_updated",
                        target_type="job",
                        target_id=job_id,
                        details=status_update
                    )

                    conn.close()

                    self.send_json_response({
                        "status": "success",
                        "message": "Job status updated successfully",
                        "job_id": job_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                else:
                    conn.close()
                    self.send_json_response({
                        "error": "No fields to update"
                    }, status=400)

            # 更新节点信息
            elif path.startswith('/api/nodes/') and path.endswith('/heartbeat'):
                node_id = path.split('/')[-2]
                heartbeat_data = body

                conn = sqlite3.connect(self.server_instance.db_path)
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE nodes SET
                        last_heartbeat = ?,
                        status = 'online',
                        updated_at = ?
                    WHERE node_id = ?
                ''', (
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    node_id
                ))

                conn.commit()
                conn.close()

                self.send_json_response({
                    "status": "success",
                    "message": "Heartbeat received",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            else:
                self.send_json_response({
                    "error": "Not Found",
                    "path": path,
                    "message": "The requested endpoint does not exist"
                }, status=404)

        except json.JSONDecodeError:
            self.send_json_response({
                "error": "Invalid JSON",
                "message": "Request body contains invalid JSON"
            }, status=400)
        except Exception as e:
            self.send_json_response({
                "error": "Internal Server Error",
                "message": str(e),
                "traceback": traceback.format_exc()
            }, status=500)

    def send_json_response(self, data, status=200):
        """发送JSON响应"""
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))

    def send_text_response(self, text, content_type='text/plain'):
        """发送文本响应"""
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(text.encode('utf-8'))

    def log_message(self, format, *args):
        """简化的日志输出"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

def start_hermes_api(host='0.0.0.0', port=8082):
    """启动HermesNexus API服务器"""

    # 创建API实例
    api_instance = HermesNexusCloudAPI(host=host, port=port)

    # 创建请求处理器
    def handler(*args, **kwargs):
        HermesAPIRequestHandler(*args, server=api_instance, **kwargs)

    # 启动服务器
    with socketserver.TCPServer((host, port), handler) as httpd:
        print(f"🚀 HermesNexus v{api_instance.version} Cloud API 启动成功")
        print(f"📍 监听地址: http://{host}:{port}")
        print(f"📊 健康检查: http://{host}:{port}/health")
        print(f"📈 监控指标: http://{host}:{port}/monitoring/metrics")
        print(f"🔧 系统状态: http://{host}:{port}/monitoring/status")
        print(f"📋 API文档: http://{host}:{port}/api")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 收到停止信号，正在关闭服务器...")
            print(f"✅ HermesNexus Cloud API 已停止")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='HermesNexus Cloud API v1.2.0')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=8082, help='监听端口')

    args = parser.parse_args()

    start_hermes_api(host=args.host, port=args.port)