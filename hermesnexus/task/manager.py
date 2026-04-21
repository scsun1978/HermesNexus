"""
任务状态管理器
"""
import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from .model import Task, TaskTemplate, TaskStatus


class TaskManager:
    """任务状态管理器"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self):
        """确保数据库表存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 启用外键约束
        cursor.execute('PRAGMA foreign_keys = ON')

        # 创建任务表（扩展现有jobs表）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS v2_tasks (
                task_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                command TEXT NOT NULL,
                target_device_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_by TEXT NOT NULL DEFAULT 'system',
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                result TEXT,
                priority TEXT DEFAULT 'medium',
                template_id TEXT,
                FOREIGN KEY (target_device_id) REFERENCES nodes(node_id)
            )
        ''')

        # 创建任务模板表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_templates (
                template_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                command_template TEXT NOT NULL,
                default_params TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL DEFAULT 'system'
            )
        ''')

        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_v2_tasks_status
            ON v2_tasks(status)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_v2_tasks_device
            ON v2_tasks(target_device_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_v2_tasks_created_at
            ON v2_tasks(created_at)
        ''')

        conn.commit()
        conn.close()

    def create_task(self, task: Task) -> bool:
        """创建任务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            task_data = task.to_dict()
            cursor.execute('''
                INSERT INTO v2_tasks (
                    task_id, name, description, command, target_device_id,
                    status, created_by, created_at, started_at, completed_at, result
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_data['task_id'],
                task_data['name'],
                task_data['description'],
                task_data['command'],
                task_data['target_device_id'],
                task_data['status'],
                task_data['created_by'],
                task_data['created_at'],
                task_data.get('started_at'),
                task_data.get('completed_at'),
                json.dumps(task_data.get('result')) if task_data.get('result') else None
            ))

            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error creating task: {e}")
            return False

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT task_id, name, description, command, target_device_id,
                       status, created_by, created_at, started_at, completed_at, result
                FROM v2_tasks WHERE task_id = ?
            ''', (task_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return self._row_to_task(row)
            return None
        except sqlite3.Error as e:
            print(f"Error getting task: {e}")
            return None

    def update_task_status(self, task_id: str, status: str,
                          result: Dict[str, Any] = None) -> bool:
        """更新任务状态"""
        if not TaskStatus.is_valid(status):
            raise ValueError(f"Invalid task status: {status}")

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 更新时间戳
            update_fields = {
                'status': status
            }

            if status == TaskStatus.RUNNING:
                update_fields['started_at'] = datetime.now().isoformat()
            elif TaskStatus.is_terminal(status):
                update_fields['completed_at'] = datetime.now().isoformat()

            # 构建UPDATE语句
            set_clause = ", ".join([f"{field} = ?" for field in update_fields.keys()])
            values = list(update_fields.values())

            # 添加result参数
            if result is not None:
                set_clause += ", result = ?"
                values.append(json.dumps(result))

            values.append(task_id)

            cursor.execute(f'''
                UPDATE v2_tasks SET {set_clause} WHERE task_id = ?
            ''', values)

            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()

            return affected_rows > 0
        except sqlite3.Error as e:
            print(f"Error updating task status: {e}")
            return False

    def list_tasks(self, device_id: str = None, status: str = None,
                   limit: int = 100, offset: int = 0) -> List[Task]:
        """列出任务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 构建查询条件
            conditions = []
            params = []

            if device_id:
                conditions.append("target_device_id = ?")
                params.append(device_id)

            if status:
                if not TaskStatus.is_valid(status):
                    raise ValueError(f"Invalid task status: {status}")
                conditions.append("status = ?")
                params.append(status)

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            cursor.execute(f'''
                SELECT task_id, name, description, command, target_device_id,
                       status, created_by, created_at, started_at, completed_at, result
                FROM v2_tasks
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', params + [limit, offset])

            rows = cursor.fetchall()
            conn.close()

            return [self._row_to_task(row) for row in rows]
        except sqlite3.Error as e:
            print(f"Error listing tasks: {e}")
            return []

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('DELETE FROM v2_tasks WHERE task_id = ?', (task_id,))
            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()

            return affected_rows > 0
        except sqlite3.Error as e:
            print(f"Error deleting task: {e}")
            return False

    def get_task_count(self, device_id: str = None, status: str = None) -> int:
        """获取任务数量"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 构建查询条件
            conditions = []
            params = []

            if device_id:
                conditions.append("target_device_id = ?")
                params.append(device_id)

            if status:
                if not TaskStatus.is_valid(status):
                    raise ValueError(f"Invalid task status: {status}")
                conditions.append("status = ?")
                params.append(status)

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            cursor.execute(f'''
                SELECT COUNT(*) FROM v2_tasks {where_clause}
            ''', params)

            count = cursor.fetchone()[0]
            conn.close()

            return count
        except sqlite3.Error as e:
            print(f"Error getting task count: {e}")
            return 0

    def _row_to_task(self, row) -> Task:
        """将数据库行转换为Task对象"""
        task_data = {
            'task_id': row[0],
            'name': row[1],
            'description': row[2],
            'command': row[3],
            'target_device_id': row[4],
            'status': row[5],
            'created_by': row[6],
            'created_at': row[7],
            'started_at': row[8],
            'completed_at': row[9],
            'result': json.loads(row[10]) if row[10] else None
        }
        return Task.from_dict(task_data)