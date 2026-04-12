"""
HermesNexus Phase 2 - Authentication Manager
认证管理器 - 支持简单Token和API Key认证
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List


class AuthManager:
    """认证管理器"""

    def __init__(self):
        """初始化认证管理器"""
        # 开发环境默认Token（仅用于开发）
        self._dev_tokens = {
            "dev-token-12345": {
                "user_id": "dev-admin",
                "username": "admin",
                "role": "admin",
                "permissions": ["*"],  # 所有权限
                "created_at": datetime.utcnow(),
                "expires_at": None,  # 永不过期
            }
        }

        # 生产环境Token存储（内存，生产环境应该用Redis）
        self._tokens = {}

        # API Keys存储
        self._api_keys = {}

        # 是否启用认证（开发环境可关闭）
        self._auth_enabled = os.getenv("AUTH_ENABLED", "true").lower() == "true"

    def is_enabled(self) -> bool:
        """检查认证是否启用"""
        return self._auth_enabled

    def enable(self) -> None:
        """启用认证（测试/运行时切换）"""
        self._auth_enabled = True

    def disable(self) -> None:
        """禁用认证（测试/运行时切换）"""
        self._auth_enabled = False

    def create_token(
        self,
        user_info=None,
        user_id: str = None,
        username: str = None,
        role: str = "user",
        permissions: List[str] = None,
        expires_hours: int = 24,
    ) -> str:
        """
        创建认证Token

        Args:
            user_info: 用户信息字典（兼容旧接口）包含 user_id, username, role, permissions
            user_id: 用户ID
            username: 用户名
            role: 角色
            permissions: 权限列表
            expires_hours: 过期时间（小时）

        Returns:
            Token字符串
        """
        # 兼容旧的user_info字典调用方式
        if user_info is not None:
            if isinstance(user_info, dict):
                user_id = user_info.get("user_id", user_id)
                username = user_info.get("username", username)
                role = user_info.get("role", role)
                permissions = user_info.get("permissions", permissions)
            else:
                # 如果user_info不是dict，可能是旧的调用方式传递了user_id
                user_id = user_info

        # 确保必填字段有默认值
        if not user_id:
            user_id = f"user-{uuid.uuid4().hex[:8]}"
        if not username:
            username = user_id

        token = f"token-{uuid.uuid4().hex[:16]}"

        expires_at = None
        if expires_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)

        self._tokens[token] = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "permissions": permissions or [],
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
        }

        return token

    def validate_token(self, token: str) -> Optional[Dict]:
        """
        验证Token

        Args:
            token: Token字符串

        Returns:
            Token信息，如果无效则返回None
        """
        if not token:
            return None

        # 检查开发环境Token
        if token in self._dev_tokens:
            return self._dev_tokens[token]

        # 检查用户Token
        if token in self._tokens:
            token_info = self._tokens[token]

            # 检查是否过期
            if (
                token_info["expires_at"]
                and datetime.utcnow() > token_info["expires_at"]
            ):
                del self._tokens[token]
                return None

            return token_info

        return None

    def create_api_key(self, user_id: str, name: str = None) -> str:
        """
        创建API Key

        Args:
            user_id: 用户ID
            name: API Key名称

        Returns:
            API Key字符串
        """
        api_key = f"sk-{uuid.uuid4().hex[:32]}"

        self._api_keys[api_key] = {
            "user_id": user_id,
            "name": name or "API Key",
            "created_at": datetime.utcnow(),
            "last_used": None,
        }

        return api_key

    def validate_api_key(self, api_key: str) -> Optional[Dict]:
        """
        验证API Key

        Args:
            api_key: API Key字符串

        Returns:
            API Key信息，如果无效则返回None
        """
        if not api_key:
            return None

        if api_key in self._api_keys:
            return self._api_keys[api_key]

        return None

    def revoke_token(self, token: str) -> bool:
        """
        撤销Token

        Args:
            token: Token字符串

        Returns:
            是否撤销成功
        """
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False

    def revoke_api_key(self, api_key: str) -> bool:
        """
        撤销API Key

        Args:
            api_key: API Key字符串

        Returns:
            是否撤销成功
        """
        if api_key in self._api_keys:
            del self._api_keys[api_key]
            return True
        return False

    def get_user_permissions(self, token: str) -> List[str]:
        """
        获取用户权限列表

        Args:
            token: Token字符串

        Returns:
            权限列表
        """
        token_info = self.validate_token(token)
        if not token_info:
            return []

        return token_info.get("permissions", [])

    def has_permission(self, token: str, permission: str) -> bool:
        """
        检查用户是否有指定权限

        Args:
            token: Token字符串
            permission: 权限名称

        Returns:
            是否有权限
        """
        permissions = self.get_user_permissions(token)

        # 检查通配符权限
        if "*" in permissions:
            return True

        return permission in permissions

    def extract_credentials(self, headers: Dict[str, str]) -> Optional[str]:
        """
        从请求头中提取认证凭据

        Args:
            headers: 请求头字典

        Returns:
            Token或API Key，如果未提供则返回None
        """
        # 检查Authorization头（Bearer Token）
        auth_header = headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # 移除"Bearer "前缀

        # 检查X-API-Key头
        api_key = headers.get("X-API-Key")
        if api_key:
            return api_key

        # 检查查询参数中的token
        # 这个通常在FastAPI依赖注入中处理

        return None


# 全局认证管理器实例
auth_manager = AuthManager()
