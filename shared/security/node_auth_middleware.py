"""
HermesNexus Phase 3 - 节点认证中间件
云边通信的节点身份验证和权限检查
"""

from typing import Optional, Dict, Any, Callable
from fastapi import Request, HTTPException, status
from functools import wraps
import logging

from shared.security.node_token_service import get_node_token_service
from shared.models.enums import ErrorCode, create_error_response

logger = logging.getLogger(__name__)


class NodeAuthMiddleware:
    """节点认证中间件"""

    def __init__(self):
        self.token_service = get_node_token_service()

    async def authenticate_node(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        验证节点身份

        Args:
            request: HTTP请求对象

        Returns:
            节点信息，如果验证失败则返回None
        """
        # 1. 提取Token
        token = self._extract_token(request)
        if not token:
            logger.warning(f"Node authentication failed: missing token - {request.url}")
            return None

        # 2. 验证Token
        payload = self.token_service.verify_token(token)
        if not payload:
            logger.warning(f"Node authentication failed: invalid token - {request.url}")
            return None

        # 3. 检查节点状态
        payload.get("node_id")
        # 这里可以添加节点状态检查，比如查询数据库验证节点是否处于活跃状态

        return payload

    def _extract_token(self, request: Request) -> Optional[str]:
        """
        从请求中提取Token

        Args:
            request: HTTP请求对象

        Returns:
            Token字符串，如果未找到则返回None
        """
        # 方法1: 从Authorization头提取 (Bearer token)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # 移除 "Bearer " 前缀

        # 方法2: 从X-Node-Token头提取
        node_token = request.headers.get("X-Node-Token")
        if node_token:
            return node_token

        # 方法3: 从查询参数提取 (用于某些特殊场景)
        query_token = request.query_params.get("node_token")
        if query_token:
            return query_token

        return None

    def check_permission(
        self, payload: Dict[str, Any], required_permission: str
    ) -> bool:
        """
        检查节点是否具有所需权限

        Args:
            payload: Token payload
            required_permission: 需要的权限

        Returns:
            是否具有权限
        """
        permissions = payload.get("permissions", [])

        # 检查通配符权限
        if "*" in permissions:
            return True

        # 检查具体权限
        return required_permission in permissions

    def log_access(self, payload: Dict[str, Any], request: Request, success: bool):
        """
        记录访问日志

        Args:
            payload: Token payload
            request: HTTP请求对象
            success: 是否成功
        """
        node_id = payload.get("node_id", "unknown")
        url = str(request.url)
        method = request.method

        if success:
            logger.info(
                f"Node access granted: node={node_id} method={method} url={url}"
            )
        else:
            logger.warning(
                f"Node access denied: node={node_id} method={method} url={url}"
            )


# 全局中间件实例
_auth_middleware = None


def get_node_auth_middleware() -> NodeAuthMiddleware:
    """获取节点认证中间件实例"""
    global _auth_middleware
    if _auth_middleware is None:
        _auth_middleware = NodeAuthMiddleware()
    return _auth_middleware


# 装饰器函数，用于路由保护
def require_node_auth(required_permission: str = None):
    """
    节点认证装饰器

    Args:
        required_permission: 需要的权限，如果为None则只验证身份

    Usage:
        @require_node_auth(NodePermission.TASK_EXECUTE)
        async def execute_task(request: Request):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从参数中获取request对象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                # 尝试从kwargs中获取
                request = kwargs.get("request")

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="无法获取请求对象",
                )

            # 获取认证中间件
            middleware = get_node_auth_middleware()

            # 验证身份
            payload = await middleware.authenticate_node(request)
            if not payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=create_error_response(
                        ErrorCode.INT_UNAUTHORIZED, details={"message": "节点认证失败"}
                    ),
                )

            # 检查权限
            if required_permission:
                if not middleware.check_permission(payload, required_permission):
                    middleware.log_access(payload, request, False)
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=create_error_response(
                            ErrorCode.INT_PERMISSION_DENIED,
                            details={
                                "message": "权限不足",
                                "required_permission": required_permission,
                            },
                        ),
                    )

            # 记录成功访问
            middleware.log_access(payload, request, True)

            # 将节点信息添加到request.state中，供后续使用
            request.state.node_id = payload.get("node_id")
            request.state.node_info = payload

            # 调用原函数
            return await func(*args, **kwargs)

        return wrapper


class NodeAuthValidator:
    """节点认证验证器 - 用于在API端点中使用"""

    def __init__(self):
        self.middleware = get_node_auth_middleware()

    async def validate_and_extract_node(self, request: Request) -> Dict[str, Any]:
        """
        验证并提取节点信息

        Args:
            request: HTTP请求对象

        Returns:
            节点信息

        Raises:
            HTTPException: 如果验证失败
        """
        payload = await self.middleware.authenticate_node(request)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=create_error_response(
                    ErrorCode.INT_UNAUTHORIZED,
                    details={"message": "节点认证失败或Token无效"},
                ),
            )

        return payload

    def check_node_permission(
        self, payload: Dict[str, Any], required_permission: str
    ) -> bool:
        """
        检查节点权限

        Args:
            payload: 节点Token payload
            required_permission: 需要的权限

        Returns:
            是否具有权限
        """
        return self.middleware.check_permission(payload, required_permission)


def get_node_auth_validator() -> NodeAuthValidator:
    """获取节点认证验证器实例"""
    return NodeAuthValidator()
