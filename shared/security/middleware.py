"""
HermesNexus Phase 2 - Authentication Middleware
认证中间件 - FastAPI依赖注入
"""

from typing import Optional
from fastapi import Header, HTTPException, Request, Depends
from fastapi.security import HTTPBearer

from shared.security.auth_manager import auth_manager
from shared.security.permissions import (
    Permission,
    get_required_permissions,
    PermissionChecker,
)
from shared.models.enums import ErrorCode

# 安全方案（用于OpenAPI文档）
security = HTTPBearer(auto_error=False)


class AuthMiddleware:
    """认证中间件"""

    @staticmethod
    async def get_current_user(
        request: Request,
        authorization: Optional[str] = Header(None),
        x_api_key: Optional[str] = Header(None),
    ) -> Optional[dict]:
        """
        获取当前用户信息

        Args:
            request: FastAPI请求对象
            authorization: Authorization头
            x_api_key: X-API-Key头

        Returns:
            用户信息字典，如果认证失败则抛出异常

        Raises:
            HTTPException: 认证失败
        """
        # 如果认证未启用，返回默认用户
        if not auth_manager.is_enabled():
            return {
                "user_id": "dev-user",
                "username": "dev-user",
                "role": "admin",
                "permissions": ["*"],
            }

        # 提取认证凭据
        token = None

        # 检查Authorization头
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]

        # 检查API Key
        elif x_api_key:
            token = x_api_key

        # 验证凭据
        user_info = None

        if token:
            # 先尝试作为Token验证
            user_info = auth_manager.validate_token(token)

            # 如果不是Token，尝试作为API Key验证
            if not user_info:
                api_key_info = auth_manager.validate_api_key(token)
                if api_key_info:
                    user_info = {
                        "user_id": api_key_info["user_id"],
                        "username": f"api_key_{api_key_info['name']}",
                        "role": "user",
                        "permissions": ["*"],  # API Key有所有权限
                        "is_api_key": True,
                    }

        if not user_info:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": {
                        "code": ErrorCode.AUTH_INVALID_CREDENTIALS,
                        "message": "Invalid or missing authentication credentials",
                        "details": "Please provide a valid Bearer token or API key",
                    }
                },
            )

        return user_info

    @staticmethod
    async def require_permissions(
        request: Request, current_user: dict = Depends(get_current_user)
    ) -> dict:
        """
        检查用户权限（基于请求路径和方法）

        Args:
            request: FastAPI请求对象
            current_user: 当前用户信息

        Returns:
            用户信息字典

        Raises:
            HTTPException: 权限不足
        """
        # 获取所需权限
        method = request.method
        path = request.url.path
        required_permissions = get_required_permissions(method, path)

        # 如果不需要权限，直接通过
        if not required_permissions:
            return current_user

        # 检查权限
        user_permissions = current_user.get("permissions", [])

        if not PermissionChecker.check_any_permission(user_permissions, required_permissions):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
                        "message": "Insufficient permissions",
                        "details": (
                            "Required permissions: " f"{[p.value for p in required_permissions]}"
                        ),
                    }
                },
            )

        return current_user

    @staticmethod
    def require_permission(permission: Permission):
        """
        权限装饰器工厂

        Args:
            permission: 所需权限

        Returns:
            FastAPI依赖函数
        """

        async def check_permission(
            current_user: dict = Depends(get_current_user),
        ) -> dict:
            user_permissions = current_user.get("permissions", [])

            if not PermissionChecker.check_permission(user_permissions, permission):
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": {
                            "code": ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
                            "message": "Insufficient permissions",
                            "details": f"Required permission: {permission.value}",
                        }
                    },
                )

            return current_user

        return check_permission

    @staticmethod
    def require_role(role: str):
        """
        角色装饰器工厂

        Args:
            role: 所需角色

        Returns:
            FastAPI依赖函数
        """

        async def check_role(current_user: dict = Depends(get_current_user)) -> dict:
            user_role = current_user.get("role")

            if user_role != role and user_role != "admin":
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": {
                            "code": ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
                            "message": "Insufficient role privileges",
                            "details": f"Required role: {role}",
                        }
                    },
                )

            return current_user

        return check_role


# 便捷依赖函数
async def get_current_user(
    authorization: Optional[str] = Header(None), x_api_key: Optional[str] = Header(None)
) -> Optional[dict]:
    """
    获取当前用户（可选认证）

    Args:
        authorization: Authorization头
        x_api_key: X-API-Key头

    Returns:
        用户信息字典，如果未提供认证则返回None
    """
    if not auth_manager.is_enabled():
        return {
            "user_id": "dev-user",
            "username": "dev-user",
            "role": "admin",
            "permissions": ["*"],
        }

    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif x_api_key:
        token = x_api_key

    if token:
        user_info = auth_manager.validate_token(token)
        if user_info:
            return user_info

        api_key_info = auth_manager.validate_api_key(token)
        if api_key_info:
            return {
                "user_id": api_key_info["user_id"],
                "username": f"api_key_{api_key_info['name']}",
                "role": "user",
                "permissions": ["*"],
                "is_api_key": True,
            }

    return None


async def require_auth(current_user: dict = Depends(get_current_user)) -> dict:
    """
    要求认证的依赖

    Args:
        current_user: 当前用户信息

    Returns:
        用户信息字典
    """
    return current_user


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    要求管理员角色的依赖

    Args:
        current_user: 当前用户信息

    Returns:
        用户信息字典

    Raises:
        HTTPException: 用户不是管理员
    """
    user_role = current_user.get("role")

    if user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
                    "message": "Insufficient role privileges",
                    "details": "Required role: admin",
                }
            },
        )

    return current_user
    """
    要求管理员角色的依赖

    Args:
        current_user: 当前用户信息

    Returns:
        用户信息字典
    """
    return current_user
