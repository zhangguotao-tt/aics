"""
对话 API 路由

POST /api/chat/message          发送消息（普通）
GET  /api/chat/history/{sid}    获取对话历史
POST /api/chat/end/{sid}        结束对话
POST /api/chat/feedback         提交消息反馈
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import get_current_user, get_optional_user
from db.database import get_db
from services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["对话"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID，不传则自动创建")


class FeedbackRequest(BaseModel):
    conversation_id: str
    message_id: str
    rating: Optional[int] = Field(None, ge=1, le=5)
    is_helpful: Optional[bool] = None
    comment: Optional[str] = None


@router.post("/message")
async def send_message(
    body: ChatRequest,
    current_user: Optional[dict] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    发送消息，返回 AI 回复（阻塞等待完整回复）

    - 未登录用户也可使用（session_id 由客户端维护）
    - 登录用户的对话会与账号关联
    """
    svc = ChatService(db)
    try:
        result = await svc.chat(
            user_message=body.message,
            session_id=body.session_id,
            user_id=current_user["user_id"] if current_user else None,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对话处理失败: {str(e)}")


@router.get("/history/{session_id}")
async def get_history(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定会话的对话历史"""
    svc = ChatService(db)
    history = await svc.get_history(session_id)
    return {"session_id": session_id, "messages": history, "count": len(history)}


@router.post("/end/{session_id}")
async def end_conversation(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """主动结束对话（清除上下文缓存）"""
    svc = ChatService(db)
    await svc.end_conversation(session_id)
    return {"message": "对话已结束", "session_id": session_id}


@router.post("/feedback")
async def submit_feedback(
    body: FeedbackRequest,
    current_user: Optional[dict] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """提交消息反馈（点赞/踩/评分）"""
    from models.conversation import MessageFeedback
    feedback = MessageFeedback(
        conversation_id=uuid.UUID(body.conversation_id),
        message_id=uuid.UUID(body.message_id),
        user_id=uuid.UUID(current_user["user_id"]) if current_user else None,
        rating=body.rating,
        is_helpful=body.is_helpful,
        comment=body.comment,
    )
    db.add(feedback)
    await db.commit()
    return {"message": "反馈已提交"}
