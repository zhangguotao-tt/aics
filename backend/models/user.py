"""
用户数据模型

表结构：
  users           - 用户账号信息
  user_sessions   - 用户登录会话
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Boolean, DateTime, Enum, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from db.database import Base


class UserRole(PyEnum):
    CUSTOMER = "customer"   # 普通客户
    AGENT = "agent"         # 客服人员
    ADMIN = "admin"         # 管理员


class UserStatus(PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.CUSTOMER, nullable=False
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    avatar_url: Mapped[str] = mapped_column(String(500), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    # 记录登录失败次数（防暴力破解）
    login_failed_count: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 关联关系
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(  # noqa F821
        "Conversation", back_populates="user"
    )

    def __repr__(self):
        return f"<User {self.username} [{self.role.value}]>"


class UserSession(Base):
    """用户登录会话（用于 JWT 黑名单和多设备管理）"""
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    device_info: Mapped[str] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="sessions")
