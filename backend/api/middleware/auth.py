"""
认证中间件 / 依赖注入

提供 FastAPI 路由的 JWT 认证依赖：
  - get_current_user: 需要登录
  - require_admin: 需要管理员权限
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from services.auth_service import AuthService
from models.user import UserRole

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    依赖注入：验证 JWT Token，返回当前用户信息

    Usage:
        @router.get("/me")
        async def me(user = Depends(get_current_user)):
            return user
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证 Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = AuthService.verify_token(credentials.credentials)
        return {
            "user_id": payload.get("sub"),
            "role": payload.get("role", "customer"),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """可选认证（登录和未登录均可访问）"""
    if not credentials:
        return None
    try:
        payload = AuthService.verify_token(credentials.credentials)
        return {"user_id": payload.get("sub"), "role": payload.get("role")}
    except ValueError:
        return None


def require_role(*roles: str):
    """
    角色权限依赖工厂

    Usage:
        @router.get("/admin/stats", dependencies=[Depends(require_role("admin"))])
    """
    async def check_role(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要角色: {', '.join(roles)}",
            )
        return user
    return check_role


# 常用权限快捷方式
require_admin = require_role("admin")
require_agent_or_admin = require_role("agent", "admin")
