"""
对话数据模型

表结构：
  conversations   - 对话会话
  messages        - 单条消息
  feedback        - 用户对回复的反馈
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Text, Float, Integer, DateTime, Enum, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from db.database import Base


class ConversationStatus(PyEnum):
    ACTIVE = "active"           # 进行中
    CLOSED = "closed"           # 正常结束
    ESCALATED = "escalated"     # 已转人工


class MessageRole(PyEnum):
    USER = "user"               # 用户消息
    ASSISTANT = "assistant"     # AI 回复
    SYSTEM = "system"           # 系统消息


class IntentType(PyEnum):
    CHITCHAT = "chitchat"           # 闲聊
    INQUIRY = "inquiry"             # 业务咨询
    COMPLAINT = "complaint"         # 投诉
    AFTER_SALES = "after_sales"     # 售后服务
    ESCALATE = "escalate"           # 请求人工
    UNKNOWN = "unknown"             # 未知


class Conversation(Base):
    """对话会话"""
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=True)  # 对话标题（自动生成）
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus), default=ConversationStatus.ACTIVE
    )
    # 对话摘要（LLM自动生成）
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    # 主要意图
    primary_intent: Mapped[IntentType] = mapped_column(
        Enum(IntentType), default=IntentType.UNKNOWN
    )
    # 对话元数据（来源渠道、设备等）
    extra_info: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    # 消息轮数
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    # 总 token 消耗
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    # 平均满意度评分
    avg_satisfaction: Mapped[float] = mapped_column(Float, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 关联
    user: Mapped["User"] = relationship("User", back_populates="conversations")  # noqa F821
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    feedback_list: Mapped[list["MessageFeedback"]] = relationship(
        "MessageFeedback", back_populates="conversation"
    )

    def __repr__(self):
        return f"<Conversation {self.session_id[:8]} [{self.status.value}]>"


class Message(Base):
    """单条消息"""
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False,
        index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 意图识别结果
    intent: Mapped[IntentType] = mapped_column(
        Enum(IntentType), default=IntentType.UNKNOWN, nullable=True
    )
    intent_confidence: Mapped[float] = mapped_column(Float, nullable=True)
    # RAG 使用的知识库来源
    rag_sources: Mapped[list] = mapped_column(JSON, default=list)
    # Token 统计
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    # 生成时延（毫秒）
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    # 是否已被用户标记为有用
    is_helpful: Mapped[bool] = mapped_column(Boolean, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message [{self.role.value}] {self.content[:30]}...>"


class MessageFeedback(Base):
    """消息反馈（点赞/踩/满意度评分）"""
    __tablename__ = "message_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # 1-5 满意度评分
    rating: Mapped[int] = mapped_column(Integer, nullable=True)
    is_helpful: Mapped[bool] = mapped_column(Boolean, nullable=True)
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="feedback_list"
    )
