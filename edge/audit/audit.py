"""
审计日志记录器

记录SSH执行器的操作日志
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from threading import Lock


logger = logging.getLogger(__name__)


class AuditLogger:
    """审计日志记录器"""

    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.audit_file = self.log_dir / "audit.log"
        self.lock = Lock()
        self.logs = []  # 内存中的日志缓存

        # 确保审计文件存在
        if not self.audit_file.exists():
            self.audit_file.write_text("")  # 创建空文件

    def log(
        self,
        action: str,
        actor: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """记录审计日志"""
        try:
            with self.lock:
                audit_entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": action,
                    "actor": actor,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "details": details or {},
                    "ip_address": ip_address,
                    "success": success,
                    "error_message": error_message,
                }

                # 追加到内存缓存
                self.logs.append(audit_entry)

                # 追加到审计日志文件
                with open(self.audit_file, "a") as f:
                    f.write(json.dumps(audit_entry) + "\n")

                logger.debug(f"📝 审计日志记录: {action} by {actor}")

        except Exception as e:
            logger.error(f"❌ 记录审计日志失败: {e}")

    def log_ssh_command(
        self, host: str, command: str, result: Dict[str, Any], actor: str = "edge_node"
    ):
        """记录SSH命令执行"""
        self.log(
            action="ssh_command",
            actor=actor,
            resource_type="ssh_command",
            resource_id=host,
            details={
                "host": host,
                "command": command,
                "exit_code": result.get("exit_code"),
                "execution_time": result.get("execution_time"),
                "success": result.get("success", False),
            },
            success=result.get("success", False),
            error_message=result.get("error"),
        )

    def log_ssh_connection(
        self,
        host: str,
        username: str,
        success: bool,
        error_message: Optional[str] = None,
    ):
        """记录SSH连接"""
        self.log(
            action="ssh_connection",
            actor=username,
            resource_type="ssh_connection",
            resource_id=host,
            details={"host": host, "username": username, "port": 22},
            success=success,
            error_message=error_message,
        )

    def get_recent_logs(self, limit: int = 100) -> list:
        """获取最近的审计日志"""
        try:
            if not self.audit_file.exists():
                return []

            with open(self.audit_file, "r") as f:
                lines = f.readlines()

            # 获取最近的日志
            recent_lines = lines[-limit:] if len(lines) > limit else lines

            audits = []
            for line in reversed(recent_lines):  # 最新的在前
                try:
                    audit = json.loads(line.strip())
                    audits.append(audit)
                except Exception:
                    continue

            return audits

        except Exception as e:
            logger.error(f"❌ 读取审计日志失败: {e}")
            return []

    def search_logs(
        self,
        action: Optional[str] = None,
        actor: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        """搜索审计日志"""
        try:
            # 使用内存中的日志缓存进行搜索
            filtered_logs = []
            for log in reversed(self.logs):  # 最新的在前
                match = True

                if action and log.get("action") != action:
                    match = False
                if actor and log.get("actor") != actor:
                    match = False
                if resource_type and log.get("resource_type") != resource_type:
                    match = False

                if match:
                    filtered_logs.append(log)

                if len(filtered_logs) >= limit:
                    break

            return filtered_logs

        except Exception as e:
            logger.error(f"❌ 搜索审计日志失败: {e}")
            return []
