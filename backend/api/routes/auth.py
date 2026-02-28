"""
认证相关 API 路由

POST /api/auth/register   注册
POST /api/auth/login      登录
POST /api/auth/logout     登出
GET  /api/auth/me         获取当前用户信息
POST /api/auth/change-password  修改密码
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import get_current_user
from db.database import get_db
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


# ── 请求/响应 Schema ──────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr
    password: str = Field(..., min_length=8, description="密码（至少8位）")
    full_name: str = Field(None, max_length=100)


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


# ── 路由 ──────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户注册"""
    svc = AuthService(db)
    try:
        user = await svc.register(
            username=body.username,
            email=body.email,
            password=body.password,
            full_name=body.full_name,
        )
        return {
            "message": "注册成功",
            "user": {"id": str(user.id), "username": user.username, "email": user.email},
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """用户登录，返回 JWT Token"""
    svc = AuthService(db)
    try:
        result = await svc.login(
            username=body.username,
            password=body.password,
            ip_address=request.client.host if request.client else None,
            device_info=request.headers.get("user-agent"),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me")
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前登录用户信息"""
    from sqlalchemy import select
    from models.user import User
    import uuid
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(current_user["user_id"]))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "created_at": user.created_at.isoformat(),
    }


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码"""
    svc = AuthService(db)
    try:
        await svc.change_password(
            current_user["user_id"], body.old_password, body.new_password
        )
        return {"message": "密码修改成功"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
