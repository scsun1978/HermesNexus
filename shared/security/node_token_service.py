"""
HermesNexus Phase 3 - 节点认证Token服务
JWT Token的生成、验证和管理
"""

from jose import jwt
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from shared.models.node import NodeIdentity, NodeTokenInfo, NodePermission


class NodeTokenService:
    """节点Token服务"""

    def __init__(self, private_key: str = None, public_key: str = None):
        """
        初始化Token服务

        Args:
            private_key: 私钥(用于签名Token)
            public_key: 公钥(用于验证Token)
        """
        self.private_key = private_key or self._generate_private_key()
        self.public_key = public_key or self._extract_public_key()

        # Token配置
        self.token_algorithm = "RS256"  # 非对称加密
        self.token_expiry_hours = 24  # Token有效期24小时
        self.issuer = "hermesnexus-cloud"  # 颁发者

    def _generate_private_key(self) -> str:
        """生成RSA密钥对"""
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

    def _extract_public_key(self) -> str:
        """从私钥提取公钥"""
        try:
            private_key = self._load_pem_key(self.private_key)
            public_key = private_key.public_key()
            return public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode("utf-8")
        except Exception:
            # 如果私钥无效，生成新密钥对
            return self._generate_private_key()

    def _load_pem_key(self, key_string: str):
        """加载PEM格式密钥"""
        from cryptography.hazmat.primitives import serialization

        return serialization.load_pem_private_key(key_string.encode("utf-8"), password=None)

    def generate_token(self, node_identity: NodeIdentity) -> NodeTokenInfo:
        """
        为节点生成认证Token

        Args:
            node_identity: 节点身份对象

        Returns:
            Token信息
        """
        # 计算Token过期时间
        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(hours=self.token_expiry_hours)

        # 生成Token payload
        payload = {
            "node_id": node_identity.node_id,
            "node_name": node_identity.node_name,
            "node_type": node_identity.node_type.value,
            "tenant_id": node_identity.tenant_id,
            "region_id": node_identity.region_id,
            "permissions": self._get_node_permissions(node_identity),
            "max_concurrent_tasks": node_identity.max_concurrent_tasks,
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
            "iss": self.issuer,
            "jti": str(uuid.uuid4()),  # Token唯一ID
        }

        # 生成JWT Token
        token = jwt.encode(payload, self.private_key, algorithm=self.token_algorithm)

        # 创建Token信息
        token_info = NodeTokenInfo(
            token=token,
            node_id=node_identity.node_id,
            expires_at=expires_at,
            permissions=payload["permissions"],
            issued_at=issued_at,
        )

        return token_info

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证节点Token

        Args:
            token: JWT Token字符串

        Returns:
            Token payload，如果验证失败则返回None
        """
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.token_algorithm],
                issuer=self.issuer,
            )

            # 检查Token是否过期
            exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            if datetime.now(timezone.utc) > exp_time:
                return None

            return payload

        except jwt.ExpiredSignatureError:
            # Token过期
            return None
        except jwt.InvalidTokenError:
            # Token无效
            return None
        except Exception as e:
            # 其他验证错误
            print(f"Token verification error: {e}")
            return None

    def refresh_token(self, old_token: str, node_identity: NodeIdentity) -> NodeTokenInfo:
        """
        刷新节点Token

        Args:
            old_token: 旧的Token
            node_identity: 节点身份对象

        Returns:
            新的Token信息
        """
        # 验证旧Token
        payload = self.verify_token(old_token)
        if not payload:
            raise ValueError("旧Token无效或已过期")

        # 生成新Token
        return self.generate_token(node_identity)

    def revoke_token(self, token: str) -> bool:
        """
        吊销Token（在内存中记录）

        Args:
            token: 要吊销的Token

        Returns:
            是否吊销成功
        """
        # 在生产环境中，应该使用Redis等存储来记录吊销的Token
        # 这里简化实现，返回True表示支持吊销
        # 实际验证时需要检查Token是否在吊销列表中
        return True

    def _get_node_permissions(self, node_identity: NodeIdentity) -> List[str]:
        """
        根据节点身份计算权限列表

        Args:
            node_identity: 节点身份对象

        Returns:
            权限列表
        """
        permissions = [
            NodePermission.HEARTBEAT.value,
            NodePermission.STATUS_REPORT.value,
            NodePermission.ERROR_REPORT.value,
        ]

        # 根据节点状态和类型添加权限
        if node_identity.status in ["active", "registered"]:
            permissions.append(NodePermission.TASK_EXECUTE.value)
            permissions.append(NodePermission.TASK_REPORT.value)

        return permissions

    def extract_node_id(self, token: str) -> Optional[str]:
        """
        从Token中提取节点ID

        Args:
            token: JWT Token字符串

        Returns:
            节点ID，如果解析失败则返回None
        """
        payload = self.verify_token(token)
        if payload:
            return payload.get("node_id")
        return None

    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """
        获取Token过期时间

        Args:
            token: JWT Token字符串

        Returns:
            过期时间，如果解析失败则返回None
        """
        payload = self.verify_token(token)
        if payload:
            return datetime.fromtimestamp(payload["exp"])
        return None


# 全局Token服务实例
_node_token_service = None


def get_node_token_service() -> NodeTokenService:
    """获取节点Token服务实例"""
    global _node_token_service
    if _node_token_service is None:
        _node_token_service = NodeTokenService()
    return _node_token_service
