"""
知识库管理 API 路由

POST /api/knowledge/upload       上传文档
GET  /api/knowledge/list         知识库列表
GET  /api/knowledge/{id}         文档详情
DELETE /api/knowledge/{id}       删除文档
POST /api/knowledge/search       语义搜索
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import require_agent_or_admin, get_current_user
from db.database import get_db
from models.knowledge import KnowledgeDocument, DocumentStatus, DocumentType

router = APIRouter(prefix="/knowledge", tags=["知识库"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON 字符串
    current_user: dict = Depends(require_agent_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """上传知识文档并异步处理（分块+向量化）"""
    import json, os, tempfile
    from pathlib import Path

    # 文件类型检查
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件类型，允许: {ALLOWED_EXTENSIONS}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"文件过大（最大 {MAX_FILE_SIZE // 1024 // 1024}MB）")

    # SHA256 去重
    from core.rag.embedder import DocumentEmbedder
    content_hash = DocumentEmbedder.compute_hash(content.decode("utf-8", errors="ignore"))

    dup = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.file_hash == content_hash)
    )
    if dup.scalar_one_or_none():
        raise HTTPException(409, "该文档已存在（内容重复）")

    # 创建文档记录
    doc = KnowledgeDocument(
        title=title,
        doc_type=DocumentType(suffix.lstrip(".")) if suffix.lstrip(".") in DocumentType.__members__ else DocumentType.TXT,
        status=DocumentStatus.PROCESSING,
        file_hash=content_hash,
        file_size=len(content),
        category=category,
        tags=json.loads(tags) if tags else [],
        created_by=uuid.UUID(current_user["user_id"]),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # 异步处理（写临时文件 → 分块 → 向量化）
    import asyncio
    asyncio.create_task(
        _process_document(str(doc.id), content, suffix, title, db)
    )

    return {
        "message": "文档已接收，正在后台处理",
        "doc_id": str(doc.id),
        "status": "processing",
    }


async def _process_document(doc_id: str, content: bytes, suffix: str, title: str, db):
    """后台异步处理文档：分块 → 向量化"""
    from core.rag.embedder import document_embedder
    from sqlalchemy import update
    try:
        text = content.decode("utf-8", errors="replace")
        chunks = await document_embedder.embed_document(
            content=text, doc_id=doc_id, source=title
        )
        # 更新状态
        from db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as new_db:
            await new_db.execute(
                update(KnowledgeDocument).where(
                    KnowledgeDocument.id == uuid.UUID(doc_id)
                ).values(
                    status=DocumentStatus.ACTIVE,
                    chunk_count=len(chunks),
                    vector_count=len(chunks),
                )
            )
            await new_db.commit()
    except Exception as e:
        from db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as new_db:
            await new_db.execute(
                update(KnowledgeDocument).where(
                    KnowledgeDocument.id == uuid.UUID(doc_id)
                ).values(status=DocumentStatus.FAILED, error_message=str(e))
            )
            await new_db.commit()


@router.get("/list")
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    category: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取知识库文档列表"""
    query = select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())
    if category:
        query = query.where(KnowledgeDocument.category == category)
    if status:
        query = query.where(KnowledgeDocument.status == DocumentStatus(status))

    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    docs = result.scalars().all()
    return {
        "items": [
            {
                "id": str(d.id), "title": d.title, "status": d.status.value,
                "category": d.category, "chunk_count": d.chunk_count,
                "created_at": d.created_at.isoformat(),
            } for d in docs
        ],
        "page": page,
        "page_size": page_size,
    }


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: dict = Depends(require_agent_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除知识文档（同时删除 ChromaDB 向量）"""
    result = await db.execute(
        select(KnowledgeDocument).where(KnowledgeDocument.id == uuid.UUID(doc_id))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "文档不存在")

    # 删除向量
    from core.rag.embedder import document_embedder
    document_embedder.delete_document(doc_id)

    await db.delete(doc)
    await db.commit()
    return {"message": "文档已删除"}


@router.post("/search")
async def semantic_search(
    query: str,
    top_k: int = 5,
    current_user: dict = Depends(get_current_user),
):
    """知识库语义搜索"""
    from core.rag.retriever import rag_retriever
    docs = await rag_retriever.retrieve(query, top_k=top_k, use_cache=False)
    return {"query": query, "results": docs, "count": len(docs)}
