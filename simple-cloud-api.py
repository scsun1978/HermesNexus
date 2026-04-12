#!/usr/bin/env python3
"""HermesNexus 简化版 Cloud API - 适用于无网络环境"""
import http.server
import socketserver
import json
import sqlite3
import os
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# 配置
PORT = 8080
DB_PATH = "/home/scsun/hermesnexus/data/hermesnexus.db"
PROJECT_ROOT = "/home/scsun/hermesnexus"

class HermesAPIHandler(http.server.BaseHTTPRequestHandler):
    """HermesNexus API请求处理器"""

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
            else:
                self.send_not_found()
        except Exception as e:
            self.send_error_response(str(e))

    def do_POST(self):
        """处理POST请求"""
        parsed_path = urllib.parse.urlparse(self.path)
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        try:
            if parsed_path.path == '/api/v1/tasks':
                data = json.loads(post_data.decode('utf-8'))
                self.create_task(data)
            elif parsed_path.path.endswith('/heartbeat'):
                node_id = parsed_path.path.split('/')[-2]
                heartbeat_data = json.loads(post_data.decode('utf-8'))
                self.handle_heartbeat(node_id, heartbeat_data)
            else:
                self.send_not_found()
        except Exception as e:
            self.send_error_response(str(e))

    def send_health_check(self):
        """健康检查端点"""
        response = {
            "status": "healthy",
            "version": "1.1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "deployment": "simplified-python3"
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

        conn.close()

        response = {
            "active_nodes": active_nodes,
            "total_tasks": total_tasks,
            "pending_tasks": pending_tasks,
            "system_status": "operational",
            "deployment_type": "simplified"
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

    def create_task(self, task_data):
        """创建新任务"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        current_time = datetime.now(timezone.utc).isoformat()

        try:
            cursor.execute('''
                INSERT INTO tasks (task_id, node_id, task_type, target, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                task_data.get("task_id", f"task-{int(datetime.now().timestamp())}"),
                task_data.get("node_id", "unknown"),
                task_data.get("task_type", "unknown"),
                json.dumps(task_data.get("target", {})),
                "pending",
                current_time
            ))

            conn.commit()
            conn.close()

            response = {
                "status": "success",
                "task_id": task_data.get("task_id"),
                "message": "Task created successfully",
                "created_at": current_time
            }
            self.send_json_response(response)

        except sqlite3.IntegrityError:
            conn.close()
            self.send_error_response("Task ID already exists", 400)

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
            "SELECT task_id, node_id, task_type, target, status, result, created_at FROM tasks WHERE task_id = ?",
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
            "created_at": row[6]
        }
        self.send_json_response(response)

    def send_tasks_list(self):
        """获取任务列表"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT task_id, node_id, task_type, status, created_at FROM tasks ORDER BY created_at DESC LIMIT 50"
        )
        rows = cursor.fetchall()

        tasks = []
        for row in rows:
            tasks.append({
                "task_id": row[0],
                "node_id": row[1],
                "task_type": row[2],
                "status": row[3],
                "created_at": row[4]
            })

        conn.close()

        response = {
            "total": len(tasks),
            "tasks": tasks
        }
        self.send_json_response(response)

    def send_json_response(self, data, status_code=200):
        """发送JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))

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
            status TEXT NOT NULL,
            result TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
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
    print("🚀 HermesNexus 简化版 Cloud API 启动中...")
    print(f"📁 项目根目录: {PROJECT_ROOT}")
    print(f"🗄️  数据库路径: {DB_PATH}")
    print(f"🌐 服务端口: {PORT}")

    # 初始化数据库
    init_database()

    # 创建HTTP服务器
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), HermesAPIHandler) as httpd:
        print(f"✅ HermesNexus Cloud API 已启动")
        print(f"🌐 访问地址: http://0.0.0.0:{PORT}")
        print(f"🏥 健康检查: http://0.0.0.0:{PORT}/health")
        print(f"📊 系统统计: http://0.0.0.0:{PORT}/api/v1/stats")
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