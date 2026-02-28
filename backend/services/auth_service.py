"""
用户认证服务

提供：
  - 用户注册 / 登录 / 刷新 Token
  - 密码哈希（bcrypt）
  - JWT 生成与验证
  - 账号锁定（防暴力破解）
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.user import User, UserRole, UserStatus, UserSession
from utils.logger import logger

# bcrypt 密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 账号锁定阈值
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 30


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 用户注册 ──────────────────────────────────────────────
    async def register(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.CUSTOMER,
    ) -> User:
        """注册新用户"""
        # 检查用户名/邮箱是否已存在
        existing = await self.db.execute(
            select(User).where(
                (User.username == username) | (User.email == email)
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("用户名或邮箱已被注册")

        user = User(
            username=username,
            email=email,
            hashed_password=self._hash_password(password),
            full_name=full_name,
            role=role,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"[Auth] 新用户注册: {username}")
        return user

    # ── 用户登录 ──────────────────────────────────────────────
    async def login(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None,
    ) -> dict:
        """
        用户登录，返回 access_token 和 refresh_token

        Raises:
            ValueError: 用户名/密码错误、账号被锁定/禁用
        """
        user = await self._get_user_by_username(username)

        # 账号状态检查
        if not user:
            raise ValueError("用户名或密码错误")
        if user.status == UserStatus.BANNED:
            raise ValueError("账号已被封禁，请联系管理员")
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            remaining = (user.locked_until - datetime.now(timezone.utc)).seconds // 60
            raise ValueError(f"账号已锁定，请 {remaining} 分钟后再试")

        # 密码验证
        if not self._verify_password(password, user.hashed_password):
            await self._handle_failed_login(user)
            raise ValueError("用户名或密码错误")

        # 登录成功：重置失败计数
        await self.db.execute(
            update(User).where(User.id == user.id).values(
                login_failed_count=0, locked_until=None
            )
        )

        # 生成 Token 对
        access_token = self._create_access_token(str(user.id), user.role.value)
        refresh_token = self._create_refresh_token(str(user.id))

        # 保存 Session
        session = UserSession(
            user_id=user.id,
            refresh_token_hash=self._hash_password(refresh_token),
            ip_address=ip_address,
            device_info=device_info,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.jwt_refresh_token_expire_days),
        )
        self.db.add(session)
        await self.db.commit()

        logger.info(f"[Auth] 用户登录成功: {username} from {ip_address}")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire_minutes * 60,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "full_name": user.full_name,
            },
        }

    # ── Token 验证 ────────────────────────────────────────────
    @staticmethod
    def verify_token(token: str) -> dict:
        """
        验证 JWT access token

        Returns:
            payload dict: {"sub": user_id, "role": "...", "exp": ...}

        Raises:
            ValueError: token 无效或已过期
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            return payload
        except JWTError as e:
            raise ValueError(f"Token 无效: {e}")

    # ── 修改密码 ──────────────────────────────────────────────
    async def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> None:
        user = await self._get_user_by_id(user_id)
        if not user or not self._verify_password(old_password, user.hashed_password):
            raise ValueError("原密码错误")
        await self.db.execute(
            update(User).where(User.id == user.id).values(
                hashed_password=self._hash_password(new_password)
            )
        )
        await self.db.commit()
        logger.info(f"[Auth] 用户修改密码: {user.username}")

    # ── 内部工具 ──────────────────────────────────────────────
    @staticmethod
    def _hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def _verify_password(plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    @staticmethod
    def _create_access_token(user_id: str, role: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        return jwt.encode(
            {"sub": user_id, "role": role, "exp": expire, "type": "access"},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    @staticmethod
    def _create_refresh_token(user_id: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )
        return jwt.encode(
            {"sub": user_id, "exp": expire, "type": "refresh"},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    async def _get_user_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def _get_user_by_id(self, user_id: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        return result.scalar_one_or_none()

    async def _handle_failed_login(self, user: User) -> None:
        """处理登录失败：累计失败次数，超限则锁定账号"""
        new_count = (user.login_failed_count or 0) + 1
        values = {"login_failed_count": new_count}
        if new_count >= MAX_FAILED_ATTEMPTS:
            values["locked_until"] = datetime.now(timezone.utc) + timedelta(
                minutes=LOCKOUT_MINUTES
            )
            logger.warning(f"[Auth] 账号锁定: {user.username}（失败{new_count}次）")
        await self.db.execute(update(User).where(User.id == user.id).values(**values))
        await self.db.commit()
