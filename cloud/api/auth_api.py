"""
HermesNexus Phase 2 - Authentication API
认证管理API
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from shared.security.auth_manager import auth_manager
from shared.security.middleware import get_current_user, require_admin

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class TokenCreateRequest(BaseModel):
    """Token创建请求"""

    username: str = Field(..., description="用户名")
    password: str = Field(
        ..., description="密码"
    )  # 开发环境简化，生产环境应该使用真实密码验证


class TokenCreateResponse(BaseModel):
    """Token创建响应"""

    token: str = Field(..., description="认证Token")
    user_id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    role: str = Field(..., description="角色")
    permissions: list = Field(..., description="权限列表")
    expires_at: str = Field(None, description="过期时间")


class ApiKeyCreateRequest(BaseModel):
    """API Key创建请求"""

    name: str = Field(None, description="API Key名称")


class ApiKeyCreateResponse(BaseModel):
    """API Key创建响应"""

    api_key: str = Field(..., description="API Key")
    name: str = Field(..., description="API Key名称")
    created_at: str = Field(..., description="创建时间")


@router.post("/token", response_model=TokenCreateResponse)
async def create_token(request: TokenCreateRequest):
    """
    创建认证Token

    开发环境简化版本：任何用户名都可以创建Token
    生产环境应该验证用户凭据
    """
    # 开发环境简化逻辑
    user_id = f"user-{request.username}"

    # 确定角色（开发环境简单规则）
    if request.username == "admin":
        role = "admin"
        permissions = ["*"]
    else:
        role = "user"
        permissions = ["asset:read", "task:read"]

    # 创建Token
    token = auth_manager.create_token(
        user_id=user_id,
        username=request.username,
        role=role,
        permissions=permissions,
        expires_hours=24,
    )

    token_info = auth_manager.validate_token(token)

    return TokenCreateResponse(
        token=token,
        user_id=token_info["user_id"],
        username=token_info["username"],
        role=token_info["role"],
        permissions=token_info["permissions"],
        expires_at=(
            token_info["expires_at"].isoformat() if token_info["expires_at"] else None
        ),
    )


@router.post("/api-keys", response_model=ApiKeyCreateResponse)
async def create_api_key(
    request: ApiKeyCreateRequest, current_user: dict = Depends(require_admin)
):
    """
    创建API Key（需要管理员权限）

    Args:
        request: API Key创建请求
        current_user: 当前用户信息

    Returns:
        API Key信息
    """
    api_key = auth_manager.create_api_key(
        user_id=current_user["user_id"], name=request.name or "API Key"
    )

    api_key_info = auth_manager.validate_api_key(api_key)

    return ApiKeyCreateResponse(
        api_key=api_key,
        name=api_key_info["name"],
        created_at=api_key_info["created_at"].isoformat(),
    )


@router.delete("/token/{token}")
async def revoke_token(token: str, current_user: dict = Depends(require_admin)):
    """
    撤销Token（需要管理员权限）

    Args:
        token: Token字符串
        current_user: 当前用户信息

    Returns:
        操作结果
    """
    success = auth_manager.revoke_token(token)

    if not success:
        raise HTTPException(status_code=404, detail="Token not found")

    return {"revoked": True}


@router.delete("/api-keys/{api_key}")
async def revoke_api_key(api_key: str, current_user: dict = Depends(require_admin)):
    """
    撤销API Key（需要管理员权限）

    Args:
        api_key: API Key字符串
        current_user: 当前用户信息

    Returns:
        操作结果
    """
    success = auth_manager.revoke_api_key(api_key)

    if not success:
        raise HTTPException(status_code=404, detail="API Key not found")

    return {"revoked": True}


@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    获取当前用户信息

    Args:
        current_user: 当前用户信息

    Returns:
        用户信息
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {
        "user_id": current_user.get("user_id"),
        "username": current_user.get("username"),
        "role": current_user.get("role"),
        "permissions": current_user.get("permissions", []),
        "is_authenticated": True,
    }


@router.get("/config")
async def get_auth_config():
    """
    获取认证配置信息

    Returns:
        认证配置
    """
    return {
        "auth_enabled": auth_manager.is_enabled(),
        "auth_methods": ["bearer_token", "api_key"],
        "default_token_expiry": "24 hours",
        "dev_mode_tokens": (
            list(auth_manager._dev_tokens.keys()) if auth_manager.is_enabled() else []
        ),
    }
