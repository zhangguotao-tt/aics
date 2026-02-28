"""
知识库数据模型

表结构：
  knowledge_documents  - 原始文档元数据
  knowledge_chunks     - 文档分块记录
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Text, Integer, Float, DateTime, Enum, JSON, Boolean, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from db.database import Base


class DocumentStatus(PyEnum):
    PENDING = "pending"         # 待处理
    PROCESSING = "processing"   # 处理中
    ACTIVE = "active"           # 已激活
    FAILED = "failed"           # 处理失败
    ARCHIVED = "archived"       # 已归档


class DocumentType(PyEnum):
    PDF = "pdf"
    WORD = "word"
    TXT = "txt"
    MARKDOWN = "markdown"
    URL = "url"
    MANUAL = "manual"           # 手动录入


class KnowledgeDocument(Base):
    """知识库原始文档"""
    __tablename__ = "knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    doc_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType), nullable=False, default=DocumentType.MANUAL
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.PENDING
    )
    # 文件信息
    file_path: Mapped[str] = mapped_column(String(1000), nullable=True)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=True)   # 字节
    file_hash: Mapped[str] = mapped_column(String(64), nullable=True)   # SHA-256 防重复
    source_url: Mapped[str] = mapped_column(String(2000), nullable=True)
    # 分类标签
    tags: Mapped[list] = mapped_column(JSON, default=list)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    # 分块统计
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    # 向量化统计
    vector_count: Mapped[int] = mapped_column(Integer, default=0)
    # 处理错误信息
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    # 扩展元数据
    extra_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    # 是否公开
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 关联
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<KnowledgeDocument '{self.title[:30]}' [{self.status.value}]>"


class KnowledgeChunk(Base):
    """文档分块记录（与 ChromaDB 向量对应）"""
    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    # 在 ChromaDB 中对应的向量 ID
    chroma_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # 分块内容
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 分块在原文中的位置
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int] = mapped_column(Integer, nullable=True)
    # 检索命中次数（用于热度统计）
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    # 最近一次检索的相似度得分
    last_score: Mapped[float] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document: Mapped["KnowledgeDocument"] = relationship(
        "KnowledgeDocument", back_populates="chunks"
    )

    def __repr__(self):
        return f"<KnowledgeChunk doc={self.document_id} idx={self.chunk_index}>"
