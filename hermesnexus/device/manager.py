"""
设备管理器 - Week 4 Day 1-2
MVP 3类设备管理实现
"""
import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from .types import (
    DeviceType, DeviceTypeFactory, DeviceCommandAdapter,
    DeviceCapabilities, DeviceValidator
)


class DeviceManager:
    """设备管理器 - 管理不同类型的网络设备"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_device_tables()

    def _ensure_device_tables(self):
        """确保设备相关表存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 启用外键约束
        cursor.execute('PRAGMA foreign_keys = ON')

        # 创建设备表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_type TEXT NOT NULL,
                hostname TEXT NOT NULL,
                vendor TEXT,
                model TEXT,
                ssh_host TEXT NOT NULL,
                ssh_port INTEGER NOT NULL,
                ssh_user TEXT NOT NULL,
                login_type TEXT NOT NULL DEFAULT 'password',
                ssh_private_key_path TEXT,
                command_style TEXT,
                timeout INTEGER DEFAULT 30,
                status TEXT DEFAULT 'unknown',
                capabilities TEXT,
                config TEXT,
                created_at TEXT NOT NULL,
                last_seen TEXT,
                FOREIGN KEY (device_type) REFERENCES device_types(device_type)
            )
        ''')

        # 创建设备类型表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_types (
                device_type TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                command_styles TEXT,
                created_at TEXT NOT NULL
            )
        ''')

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_hostname ON devices(hostname)')

        # 初始化设备类型
        self._initialize_device_types(cursor)

        conn.commit()
        conn.close()

    def _initialize_device_types(self, cursor):
        """初始化设备类型数据"""
        device_types = [
            {
                'device_type': 'router',
                'name': '路由器',
                'description': '网络路由设备，负责数据包转发和路由选择',
                'command_styles': json.dumps(['cisco_ios', 'huawei_vrp', 'junos']),
                'created_at': datetime.now().isoformat()
            },
            {
                'device_type': 'switch',
                'name': '交换机',
                'description': '网络交换设备，负责局域网内数据包交换',
                'command_styles': json.dumps(['cisco_ios', 'huawei_vrp']),
                'created_at': datetime.now().isoformat()
            },
            {
                'device_type': 'server',
                'name': '服务器',
                'description': '计算服务器，提供计算、存储和应用服务',
                'command_styles': json.dumps(['linux_bash', 'windows_powershell']),
                'created_at': datetime.now().isoformat()
            }
        ]

        for device_type_info in device_types:
            cursor.execute('''
                INSERT OR IGNORE INTO device_types (device_type, name, description, command_styles, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                device_type_info['device_type'],
                device_type_info['name'],
                device_type_info['description'],
                device_type_info['command_styles'],
                device_type_info['created_at']
            ))

    def register_device(self, device_config: dict) -> tuple[bool, str, Optional[str]]:
        """注册设备"""
        try:
            # 验证设备类型
            device_type = device_config.get('device_type')
            if not device_type:
                return False, "设备类型不能为空", None

            # 验证设备配置
            is_valid, errors = DeviceValidator.validate_device_config(device_type, device_config)
            if not is_valid:
                return False, f"设备配置验证失败: {', '.join(errors)}", None

            # 创建设备配置
            full_config = DeviceTypeFactory.create_config(device_type, device_config)

            # 保存到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            device_id = full_config.get('node_id') or full_config.get('hostname')

            cursor.execute('''
                INSERT INTO devices (
                    device_id, device_type, hostname, vendor, model,
                    ssh_host, ssh_port, ssh_user, login_type, ssh_private_key_path,
                    command_style, timeout, status, capabilities, config, created_at, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                device_id,
                full_config['device_type'],
                full_config['hostname'],
                full_config.get('vendor'),
                full_config.get('model'),
                full_config.get('ssh_host', full_config.get('hostname')),
                full_config['ssh_port'],
                full_config.get('ssh_user'),
                full_config['login_type'],
                full_config.get('ssh_private_key_path'),
                full_config.get('command_style'),
                full_config.get('timeout', 30),
                'unknown',
                json.dumps(DeviceCapabilities.get_capabilities(device_type)),
                json.dumps(full_config),
                datetime.now().isoformat(),
                None
            ))

            conn.commit()
            conn.close()

            return True, "设备注册成功", device_id

        except sqlite3.IntegrityError as e:
            return False, f"设备已存在或数据完整性错误: {e}", None
        except Exception as e:
            return False, f"设备注册失败: {e}", None

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取设备信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT device_id, device_type, hostname, vendor, model,
                       ssh_host, ssh_port, ssh_user, login_type, command_style,
                       timeout, status, capabilities, config, created_at, last_seen
                FROM devices WHERE device_id = ?
            ''', (device_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return self._row_to_device(row)
            return None
        except Exception as e:
            print(f"Error getting device: {e}")
            return None

    def list_devices(self, device_type: str = None, status: str = None,
                     limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """列出设备"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 构建查询条件
            conditions = []
            params = []

            if device_type:
                conditions.append("device_type = ?")
                params.append(device_type)

            if status:
                conditions.append("status = ?")
                params.append(status)

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            cursor.execute(f'''
                SELECT device_id, device_type, hostname, vendor, model,
                       ssh_host, ssh_port, ssh_user, login_type, command_style,
                       timeout, status, capabilities, config, created_at, last_seen
                FROM devices
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', params + [limit, offset])

            rows = cursor.fetchall()
            conn.close()

            return [self._row_to_device(row) for row in rows]
        except Exception as e:
            print(f"Error listing devices: {e}")
            return []

    def update_device_status(self, device_id: str, status: str) -> bool:
        """更新设备状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE devices SET status = ?, last_seen = ?
                WHERE device_id = ?
            ''', (status, datetime.now().isoformat(), device_id))

            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()

            return affected_rows > 0
        except Exception as e:
            print(f"Error updating device status: {e}")
            return False

    def get_device_capabilities(self, device_id: str) -> Dict[str, Any]:
        """获取设备能力"""
        device = self.get_device(device_id)
        if not device:
            return {}

        try:
            capabilities = device.get('capabilities', {})
            if isinstance(capabilities, str):
                return json.loads(capabilities)
            return capabilities
        except:
            return {}

    def _row_to_device(self, row) -> Dict[str, Any]:
        """将数据库行转换为设备字典"""
        device = {
            'device_id': row[0],
            'device_type': row[1],
            'hostname': row[2],
            'vendor': row[3],
            'model': row[4],
            'ssh_host': row[5],
            'ssh_port': row[6],
            'ssh_user': row[7],
            'login_type': row[8],
            'command_style': row[9],
            'timeout': row[10],
            'status': row[11],
            'capabilities': json.loads(row[12]) if row[12] else {},
            'config': json.loads(row[13]) if row[13] else {},
            'created_at': row[14],
            'last_seen': row[15]
        }

        # Extract device-specific fields from config for easier access
        if device['config']:
            # Add common fields that might be in config
            for field in ['ports', 'os_type', 'os_version', 'architecture', 'ssh_private_key_path']:
                if field in device['config'] and field not in device:
                    device[field] = device['config'][field]

        return device


class DeviceCommandGenerator:
    """设备命令生成器 - 为不同设备类型生成适配命令"""

    def __init__(self, device_manager: DeviceManager):
        self.device_manager = device_manager

    def generate_command(self, device_id: str, template_command: str) -> str:
        """为特定设备生成适配命令"""
        device = self.device_manager.get_device(device_id)
        if not device:
            raise ValueError(f"Device not found: {device_id}")

        # 使用命令适配器
        adapted_command = DeviceCommandAdapter.adapt_command_for_device(
            template_command, device
        )

        return adapted_command

    def generate_inspection_command(self, device_id: str) -> str:
        """生成巡检命令"""
        device = self.device_manager.get_device(device_id)
        if not device:
            raise ValueError(f"Device not found: {device_id}")

        device_type = device['device_type']

        if device_type == 'router':
            return self._generate_router_inspection(device)
        elif device_type == 'switch':
            return self._generate_switch_inspection(device)
        elif device_type == 'server':
            return self._generate_server_inspection(device)
        else:
            return "echo 'Unsupported device type'"

    def _generate_router_inspection(self, device: dict) -> str:
        """生成路由器巡检命令"""
        vendor = device.get('vendor', 'cisco').lower()

        if vendor == 'cisco':
            return 'show version && show ip interface brief && show ip route'
        elif vendor == 'huawei':
            return 'display version && display ip interface brief && display ip routing-table'
        else:
            return 'show version && show interface && show route'

    def _generate_switch_inspection(self, device: dict) -> str:
        """生成交换机巡检命令"""
        vendor = device.get('vendor', 'cisco').lower()

        if vendor == 'cisco':
            return 'show version && show interface status && show mac address-table'
        elif vendor == 'huawei':
            return 'display version && display interface brief && display mac-address'
        else:
            return 'show version && show interface && show mac'

    def _generate_server_inspection(self, device: dict) -> str:
        """生成服务器巡检命令"""
        return 'uptime && df -h && free -h && netstat -an | head -20'