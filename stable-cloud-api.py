#!/usr/bin/env python3
"""HermesNexus 稳定版 Cloud API - 修复结果回写"""
import http.server
import socketserver
import json
import sqlite3
import os
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
import traceback

# 配置
PORT = 8080
DB_PATH = "/home/scsun/hermesnexus/data/hermesnexus.db"
PROJECT_ROOT = "/home/scsun/hermesnexus"

class StableAPIHandler(http.server.BaseHTTPRequestHandler):
    """稳定的API处理器 - 修复结果回写问题"""

    def do_GET(self):
        """处理GET请求"""
        parsed_path = urllib.parse.urlparse(self.path)

        try:
            if parsed_path.path == '/health':
                self.send_health_check()
            elif parsed_path.path == '/api/v1/stats':
                self.send_stats()
            elif parsed_path.path == '/api/v1/nodes':
                self.send_nodes()
            elif parsed_path.path.startswith('/api/v1/tasks/'):
                task_id = parsed_path.path.split('/')[-1]
                self.send_task_detail(task_id)
            elif parsed_path.path == '/api/v1/tasks':
                self.send_tasks_list()
            elif parsed_path.path == '/api/v1/jobs':
                self.send_jobs_list()
            elif parsed_path.path == '/api/v1/devices':
                self.send_devices_list()
            elif parsed_path.path == '/api/v1/events':
                self.send_events_list()
            elif parsed_path.path == '/api/v1/audit_logs':
                self.send_audit_logs()
            else:
                self.send_not_found()
        except Exception as e:
            self.log_error(f"GET error: {e}")
            self.send_error_response(str(e))

    def do_POST(self):
        """处理POST请求"""
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length > 0 else b''

            if parsed_path.path == '/api/v1/tasks':
                data = json.loads(post_data.decode('utf-8'))
                self.create_task(data)
            elif parsed_path.path == '/api/v1/jobs':
                data = json.loads(post_data.decode('utf-8'))
                self.create_task(data)  # jobs是tasks的别名，使用相同的创建逻辑
            elif parsed_path.path == '/api/v1/devices':
                data = json.loads(post_data.decode('utf-8'))
                self.create_device(data)
            elif parsed_path.path.endswith('/heartbeat'):
                node_id = parsed_path.path.split('/')[-2]
                heartbeat_data = json.loads(post_data.decode('utf-8'))
                self.handle_heartbeat(node_id, heartbeat_data)
            elif '/result' in parsed_path.path:
                # 处理任务结果回写 - 更灵活的URL匹配
                parts = parsed_path.path.split('/')
                # 查找 result 所在位置
                result_index = -1
                for i, part in enumerate(parts):
                    if part == 'result':
                        result_index = i
                        break

                if result_index >= 0 and result_index >= 6:
                    # URL结构: /api/v1/nodes/{node_id}/tasks/{task_id}/result
                    # parts: ['', 'api', 'v1', 'nodes', '{node_id}', 'tasks', '{task_id}', 'result']
                    node_id = parts[4]  # 修正: node_id 在 parts[4]
                    task_id = parts[6]  # 修正: task_id 在 parts[6]
                    result_data = json.loads(post_data.decode('utf-8'))
                    self.handle_task_result_stable(node_id, task_id, result_data)
                else:
                    self.send_not_found()
            else:
                self.send_not_found()
        except json.JSONDecodeError as e:
            self.log_error(f"JSON decode error: {e}")
            try:
                self.send_error_response(f"Invalid JSON: {str(e)}", 400)
            except:
                pass
        except Exception as e:
            self.log_error(f"POST error: {e}")
            self.log_error(f"Traceback: {traceback.format_exc()}")
            try:
                self.send_error_response(f"Internal error: {str(e)}", 500)
            except:
                pass

    def handle_task_result_stable(self, node_id, task_id, result_data):
        """稳定的任务结果回写处理"""
        self.log_info(f"📥 收到任务结果回写: {node_id}/{task_id}")

        conn = None
        try:
            # 确定任务状态
            task_status = "completed"
            if result_data.get("success") == False:
                task_status = "failed"

            self.log_info(f"📝 准备更新任务状态: {task_id} -> {task_status}")

            # 连接数据库并更新
            conn = sqlite3.connect(DB_PATH, timeout=10.0)
            cursor = conn.cursor()
            current_time = datetime.now(timezone.utc).isoformat()

            # 检查任务是否存在
            cursor.execute("SELECT task_id FROM tasks WHERE task_id = ? AND node_id = ?", (task_id, node_id))
            if not cursor.fetchone():
                self.log_error(f"任务不存在: {task_id}")
                self.send_error_response("Task not found", 404)
                return

            # 更新任务状态和结果
            cursor.execute('''
                UPDATE tasks
                SET status = ?,
                    result = ?,
                    completed_at = ?,
                    updated_at = ?
                WHERE task_id = ? AND node_id = ?
            ''', (
                task_status,
                json.dumps(result_data, ensure_ascii=False),
                current_time,
                current_time,
                task_id,
                node_id
            ))

            # 记录任务完成事件
            try:
                import random
                event_id = f"event-{int(datetime.now().timestamp()*1000)}-{random.randint(1000,9999)}-{task_id}"
                event_type = f"task_{task_status}"
                cursor.execute('''
                    INSERT INTO events (event_id, event_type, entity_type, entity_id, data, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    event_id,
                    event_type,
                    "task",
                    task_id,
                    json.dumps({"node_id": node_id, "status": task_status}, ensure_ascii=False),
                    current_time
                ))
            except Exception as e:
                self.log_error(f"事件记录失败: {e}")

            # 记录审计日志
            try:
                import random
                log_id = f"audit-{int(datetime.now().timestamp()*1000)}-{random.randint(1000,9999)}-{task_id}"
                cursor.execute('''
                    INSERT INTO audit_logs (log_id, action, entity_type, entity_id, details, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    log_id,
                    f"task_result_{task_status}",
                    "task",
                    task_id,
                    json.dumps({
                        "node_id": node_id,
                        "task_status": task_status,
                        "success": result_data.get("success"),
                        "completed_at": current_time
                    }, ensure_ascii=False),
                    current_time
                ))
            except Exception as e:
                self.log_error(f"审计日志记录失败: {e}")

            conn.commit()
            conn.close()
            conn = None

            self.log_info(f"✅ 数据库更新成功: {task_id}")

            # 发送成功响应
            response = {
                "status": "success",
                "task_id": task_id,
                "node_id": node_id,
                "updated_status": task_status,
                "result_received": True,
                "timestamp": current_time
            }
            self.send_json_response(response)
            self.log_info(f"✅ 任务结果回写成功: {task_id} -> {task_status}")

        except sqlite3.Error as e:
            self.log_error(f"数据库错误: {e}")
            try:
                self.send_error_response(f"Database error: {str(e)}", 500)
            except:
                pass
        except Exception as e:
            self.log_error(f"结果回写异常: {e}")
            self.log_error(f"Traceback: {traceback.format_exc()}")
            try:
                self.send_error_response(f"Result writeback error: {str(e)}", 500)
            except:
                pass
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def send_health_check(self):
        """健康检查端点"""
        response = {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "deployment": "production-mvp",
            "build_date": "2026-04-11"
        }
        self.send_json_response(response)

    def send_stats(self):
        """系统统计信息"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM nodes WHERE status = 'active'")
        active_nodes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks")
        total_tasks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
        pending_tasks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
        completed_tasks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'failed'")
        failed_tasks = cursor.fetchone()[0]

        conn.close()

        response = {
            "active_nodes": active_nodes,
            "total_tasks": total_tasks,
            "pending_tasks": pending_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "system_status": "operational"
        }
        self.send_json_response(response)

    def send_nodes(self):
        """节点列表"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT node_id, name, status, last_heartbeat FROM nodes")
        rows = cursor.fetchall()

        nodes = []
        for row in rows:
            nodes.append({
                "node_id": row[0],
                "name": row[1],
                "status": row[2],
                "last_heartbeat": row[3] or "Never"
            })

        conn.close()

        response = {
            "total": len(nodes),
            "nodes": nodes
        }
        self.send_json_response(response)

    def create_device(self, device_data):
        """创建新设备"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        current_time = datetime.now(timezone.utc).isoformat()

        try:
            device_id = device_data.get("device_id", f"device-{int(datetime.now().timestamp())}")
            device_name = device_data.get("name", device_id)
            device_type = device_data.get("device_type", "edge_node")

            # MVP阶段：设备作为节点管理
            cursor.execute('''
                INSERT OR REPLACE INTO nodes (node_id, name, status, last_heartbeat, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                device_id,
                device_name,
                "active",
                current_time,
                current_time
            ))

            conn.commit()
            conn.close()

            response = {
                "status": "success",
                "device_id": device_id,
                "name": device_name,
                "device_type": device_type,
                "message": "Device created successfully",
                "created_at": current_time
            }
            self.send_json_response(response)

        except Exception as e:
            conn.close()
            self.log_error(f"设备创建失败: {e}")
            self.send_error_response(str(e), 500)

    def create_task(self, task_data):
        """创建新任务"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        current_time = datetime.now(timezone.utc).isoformat()

        try:
            task_id = task_data.get("task_id", f"task-{int(datetime.now().timestamp())}")

            cursor.execute('''
                INSERT INTO tasks (task_id, node_id, task_type, target, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                task_id,
                task_data.get("node_id", "unknown"),
                task_data.get("task_type", "unknown"),
                json.dumps(task_data.get("target", {}), ensure_ascii=False),
                "pending",
                current_time
            ))

            # 记录任务创建事件
            try:
                import random
                cursor.execute('''
                    INSERT INTO events (event_id, event_type, entity_type, entity_id, data, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    f"event-{int(datetime.now().timestamp()*1000)}-{random.randint(1000,9999)}-{task_id}",
                    "task_created",
                    "task",
                    task_id,
                    json.dumps({"task_type": task_data.get("task_type")}, ensure_ascii=False),
                    current_time
                ))
            except Exception as e:
                self.log_error(f"任务创建事件记录失败: {e}")

            # 记录任务创建审计日志
            try:
                import random
                cursor.execute('''
                    INSERT INTO audit_logs (log_id, action, entity_type, entity_id, details, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    f"audit-{int(datetime.now().timestamp()*1000)}-{random.randint(1000,9999)}-{task_id}",
                    "task_created",
                    "task",
                    task_id,
                    json.dumps({
                        "node_id": task_data.get("node_id"),
                        "task_type": task_data.get("task_type"),
                        "status": "pending"
                    }, ensure_ascii=False),
                    current_time
                ))
            except Exception as e:
                self.log_error(f"任务创建审计日志记录失败: {e}")

            conn.commit()
            conn.close()

            response = {
                "status": "success",
                "task_id": task_id,
                "current_status": "pending",
                "message": "Task created successfully",
                "created_at": current_time
            }
            self.send_json_response(response)
            self.log_info(f"✅ 任务创建成功: {task_id}")

        except sqlite3.IntegrityError:
            conn.close()
            self.send_error_response("Task ID already exists", 400)
        except Exception as e:
            conn.close()
            self.log_error(f"任务创建失败: {e}")
            self.send_error_response(str(e), 500)

    def handle_heartbeat(self, node_id, heartbeat_data):
        """处理节点心跳"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        current_time = datetime.now(timezone.utc).isoformat()

        cursor.execute('''
            INSERT OR REPLACE INTO nodes (node_id, name, status, last_heartbeat, created_at)
            VALUES (?, ?, ?, ?, COALESCE((SELECT created_at FROM nodes WHERE node_id = ?), CURRENT_TIMESTAMP))
        ''', (
            node_id,
            heartbeat_data.get("name", node_id),
            "active",
            current_time,
            node_id
        ))

        conn.commit()
        conn.close()

        response = {
            "status": "success",
            "timestamp": current_time,
            "node_id": node_id
        }
        self.send_json_response(response)

    def send_task_detail(self, task_id):
        """获取任务详情"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT task_id, node_id, task_type, target, status, result, created_at, completed_at FROM tasks WHERE task_id = ?",
            (task_id,)
        )
        row = cursor.fetchone()

        conn.close()

        if not row:
            self.send_not_found()
            return

        response = {
            "task_id": row[0],
            "node_id": row[1],
            "task_type": row[2],
            "target": json.loads(row[3]),
            "status": row[4],
            "result": json.loads(row[5]) if row[5] else None,
            "created_at": row[6],
            "completed_at": row[7]
        }
        self.send_json_response(response)

    def send_tasks_list(self):
        """获取任务列表"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT task_id, node_id, task_type, status, created_at, completed_at FROM tasks ORDER BY created_at DESC LIMIT 50")
        rows = cursor.fetchall()

        tasks = []
        for row in rows:
            tasks.append({
                "task_id": row[0],
                "node_id": row[1],
                "task_type": row[2],
                "status": row[3],
                "created_at": row[4],
                "completed_at": row[5]
            })

        conn.close()

        response = {
            "total": len(tasks),
            "tasks": tasks
        }
        self.send_json_response(response)

    def send_jobs_list(self):
        """获取作业列表（jobs是tasks的别名）"""
        return self.send_tasks_list()

    def send_devices_list(self):
        """获取设备列表"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # MVP阶段：节点作为设备管理的基础
        cursor.execute("SELECT node_id, name, status, last_heartbeat FROM nodes")
        rows = cursor.fetchall()

        devices = []
        for row in rows:
            devices.append({
                "device_id": row[0],
                "name": row[1],
                "status": row[2],
                "last_seen": row[3] or "Never",
                "device_type": "edge_node",
                "capabilities": ["ssh_command", "system_test", "test"]
            })

        conn.close()

        response = {
            "total": len(devices),
            "devices": devices
        }
        self.send_json_response(response)

    def send_events_list(self):
        """获取事件列表"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT event_id, event_type, entity_type, entity_id, data, timestamp FROM events ORDER BY timestamp DESC LIMIT 50")
        rows = cursor.fetchall()

        events = []
        for row in rows:
            events.append({
                "event_id": row[0],
                "event_type": row[1],
                "entity_type": row[2],
                "entity_id": row[3],
                "data": json.loads(row[4]),
                "timestamp": row[5]
            })

        conn.close()

        response = {
            "total": len(events),
            "events": events
        }
        self.send_json_response(response)

    def send_audit_logs(self):
        """获取审计日志列表"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT log_id, action, entity_type, entity_id, details, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT 50")
        rows = cursor.fetchall()

        logs = []
        for row in rows:
            logs.append({
                "log_id": row[0],
                "action": row[1],
                "entity_type": row[2],
                "entity_id": row[3],
                "details": json.loads(row[4]),
                "timestamp": row[5]
            })

        conn.close()

        response = {
            "total": len(logs),
            "audit_logs": logs
        }
        self.send_json_response(response)

    def send_json_response(self, data, status_code=200):
        """发送JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8'))

    def send_error_response(self, message, status_code=500):
        """发送错误响应"""
        response = {
            "status": "error",
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.send_json_response(response, status_code)

    def send_not_found(self):
        """发送404响应"""
        response = {
            "status": "error",
            "message": "Endpoint not found",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.send_json_response(response, 404)

    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

    def log_info(self, message):
        """信息日志"""
        self.log_message(f"ℹ️ {message}")

    def log_error(self, message):
        """错误日志"""
        self.log_message(f"❌ {message}")

def init_database():
    """初始化数据库"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 创建节点表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nodes (
            node_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            last_heartbeat TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建任务表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            node_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            target TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            result TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            error_message TEXT,
            error_code TEXT
        )
    ''')

    # 创建事件表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            data TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建审计日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            log_id TEXT PRIMARY KEY,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            details TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建示例节点
    cursor.execute('''
        INSERT OR REPLACE INTO nodes (node_id, name, status, last_heartbeat)
        VALUES ('dev-edge-node-001', '开发服务器边缘节点', 'active', datetime('now'))
    ''')

    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")

def main():
    """主函数"""
    print("🚀 HermesNexus 稳定版 Cloud API 启动中...")
    print(f"📁 项目根目录: {PROJECT_ROOT}")
    print(f"🗄️  数据库路径: {DB_PATH}")
    print(f"🌐 服务端口: {PORT}")
    print("🔧 关键修复: 任务结果回写接口稳定性")

    # 初始化数据库
    init_database()

    # 创建HTTP服务器
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), StableAPIHandler) as httpd:
        print(f"✅ HermesNexus Cloud API 已启动")
        print(f"🌐 访问地址: http://0.0.0.0:{PORT}")
        print(f"🏥 健康检查: http://0.0.0.0:{PORT}/health")
        print(f"📊 系统统计: http://0.0.0.0:{PORT}/api/v1/stats")
        print(f"📋 任务管理: http://0.0.0.0:{PORT}/api/v1/tasks")
        print(f"📝 事件记录: http://0.0.0.0:{PORT}/api/v1/events")
        print(f"🔍 审计日志: http://0.0.0.0:{PORT}/api/v1/audit_logs")
        print("")
        print("🔥 关键功能: 稳定的任务结果回写接口")
        print("   POST /api/v1/nodes/{node_id}/tasks/{task_id}/result")
        print("")
        print("按 Ctrl+C 停止服务")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 服务正在停止...")
            httpd.shutdown()
            print("✅ 服务已停止")

if __name__ == "__main__":
    main()