"""
管理后台 API 路由

GET /api/admin/stats          系统统计
GET /api/admin/conversations  对话列表
GET /api/admin/users          用户列表
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import require_admin
from db.database import get_db
from models.conversation import Conversation, Message
from models.user import User
from models.knowledge import KnowledgeDocument

router = APIRouter(prefix="/admin", tags=["管理后台"])


@router.get("/stats")
async def get_stats(
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """系统总览统计"""
    user_count = await db.scalar(select(func.count()).select_from(User))
    conv_count = await db.scalar(select(func.count()).select_from(Conversation))
    msg_count = await db.scalar(select(func.count()).select_from(Message))
    doc_count = await db.scalar(select(func.count()).select_from(KnowledgeDocument))

    return {
        "users": user_count,
        "conversations": conv_count,
        "messages": msg_count,
        "knowledge_documents": doc_count,
    }


@router.get("/conversations")
async def list_conversations(
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取所有对话列表"""
    result = await db.execute(
        select(Conversation)
        .order_by(Conversation.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    convs = result.scalars().all()
    return {
        "items": [
            {
                "id": str(c.id),
                "session_id": c.session_id,
                "status": c.status.value,
                "intent": c.primary_intent.value,
                "turn_count": c.turn_count,
                "started_at": c.started_at.isoformat(),
            } for c in convs
        ],
        "page": page,
    }


@router.get("/users")
async def list_users(
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取用户列表"""
    result = await db.execute(
        select(User).order_by(User.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()
    return {
        "items": [
            {
                "id": str(u.id), "username": u.username, "email": u.email,
                "role": u.role.value, "status": u.status.value,
                "created_at": u.created_at.isoformat(),
            } for u in users
        ],
        "page": page,
    }
