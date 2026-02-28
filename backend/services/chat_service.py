"""
对话管理服务

核心编排逻辑，串联：意图识别 → RAG检索 → Prompt组装 → LLM推理 → 记忆更新
"""
from __future__ import annotations

import time
import uuid
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.intent.classifier import intent_classifier, IntentResult
from core.llm.client import get_llm_client
from core.llm.prompt_manager import prompt_manager
from core.memory.conversation_memory import ConversationMemory
from core.rag.retriever import rag_retriever
from models.conversation import (
    Conversation, Message, MessageRole, IntentType, ConversationStatus
)
from utils.logger import logger


class ChatService:
    """
    对话编排服务

    完整处理流程：
      1. 加载/创建对话会话
      2. 意图识别
      3. RAG 知识库检索
      4. 构建 Prompt（System + RAG上下文 + 历史 + 用户消息）
      5. LLM 推理（普通 or 流式）
      6. 持久化消息到 DB
      7. 更新 Redis 记忆
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_client()

    # ── 普通对话（等待完整回复）─────────────────────────────
    async def chat(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """
        处理用户消息，返回完整 AI 回复

        Returns:
            {
                "session_id": "...",
                "reply": "AI回复内容",
                "intent": "inquiry",
                "rag_sources": [...],
                "tokens": {...},
                "latency_ms": 123,
            }
        """
        start = time.time()
        session_id = session_id or str(uuid.uuid4())
        memory = ConversationMemory(session_id)

        # 1. 意图识别
        intent_result = await intent_classifier.classify(user_message)
        logger.info(
            f"[Chat] session={session_id[:8]} intent={intent_result.intent} "
            f"confidence={intent_result.confidence:.2f}"
        )

        # 2. RAG 检索
        rag_docs = await rag_retriever.retrieve(user_message)

        # 3. 构建 System Prompt
        scene = prompt_manager.intent_to_scene(intent_result.intent)
        system_prompt = prompt_manager.build_rag_system_prompt(scene, rag_docs)

        # 4. 获取对话历史
        history = await memory.get_recent()

        # 5. 调用 LLM
        reply, usage = await self.llm.chat(
            messages=history + [{"role": "user", "content": user_message}],
            system_prompt=system_prompt,
        )

        latency_ms = int((time.time() - start) * 1000)

        # 6. 更新记忆
        await memory.add_user_message(user_message)
        await memory.add_assistant_message(reply)

        # 7. 持久化到 DB
        await self._save_messages(
            session_id=session_id,
            user_id=user_id,
            user_message=user_message,
            reply=reply,
            intent_result=intent_result,
            rag_sources=[{"source": d["source"], "score": d["score"]} for d in rag_docs],
            usage=usage,
            latency_ms=latency_ms,
        )

        return {
            "session_id": session_id,
            "reply": reply,
            "intent": intent_result.intent,
            "intent_confidence": intent_result.confidence,
            "rag_sources": [d["source"] for d in rag_docs],
            "tokens": usage,
            "latency_ms": latency_ms,
        }

    # ── 流式对话（逐 Token 输出）────────────────────────────
    async def stream_chat(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        流式处理，逐 Token yield（供 WebSocket 使用）

        Usage:
            async for token in chat_service.stream_chat("你好"):
                await websocket.send_text(token)
        """
        session_id = session_id or str(uuid.uuid4())
        memory = ConversationMemory(session_id)

        # 意图 & RAG（并发执行）
        import asyncio
        intent_task = asyncio.create_task(intent_classifier.classify(user_message))
        rag_task = asyncio.create_task(rag_retriever.retrieve(user_message))
        intent_result, rag_docs = await asyncio.gather(intent_task, rag_task)

        scene = prompt_manager.intent_to_scene(intent_result.intent)
        system_prompt = prompt_manager.build_rag_system_prompt(scene, rag_docs)
        history = await memory.get_recent()

        # 流式 LLM 推理
        full_reply = ""
        async for token in self.llm.stream_chat(
            messages=history + [{"role": "user", "content": user_message}],
            system_prompt=system_prompt,
        ):
            full_reply += token
            yield token

        # 流式完成后更新记忆 & 持久化
        await memory.add_user_message(user_message)
        await memory.add_assistant_message(full_reply)
        await self._save_messages(
            session_id=session_id,
            user_id=user_id,
            user_message=user_message,
            reply=full_reply,
            intent_result=intent_result,
            rag_sources=[{"source": d["source"], "score": d["score"]} for d in rag_docs],
            usage={},
            latency_ms=0,
        )

    # ── 获取对话历史 ─────────────────────────────────────────
    async def get_history(self, session_id: str) -> list[dict]:
        """从 Redis 获取对话历史"""
        memory = ConversationMemory(session_id)
        return await memory.get_history()

    # ── 结束对话 ─────────────────────────────────────────────
    async def end_conversation(self, session_id: str) -> None:
        """结束对话，清除缓存并更新 DB 状态"""
        memory = ConversationMemory(session_id)
        await memory.clear()
        # 更新对话状态
        from sqlalchemy import select, update
        await self.db.execute(
            update(Conversation)
            .where(Conversation.session_id == session_id)
            .values(status=ConversationStatus.CLOSED)
        )
        await self.db.commit()
        logger.info(f"[Chat] 对话已关闭: {session_id[:8]}")

    # ── 内部：持久化消息 ──────────────────────────────────────
    async def _save_messages(
        self,
        session_id: str,
        user_id: Optional[str],
        user_message: str,
        reply: str,
        intent_result: IntentResult,
        rag_sources: list,
        usage: dict,
        latency_ms: int,
    ) -> None:
        """异步保存用户消息和AI回复到 PostgreSQL"""
        try:
            from sqlalchemy import select

            # 查找或创建 Conversation
            result = await self.db.execute(
                select(Conversation).where(Conversation.session_id == session_id)
            )
            conv = result.scalar_one_or_none()
            if not conv:
                conv = Conversation(
                    session_id=session_id,
                    user_id=uuid.UUID(user_id) if user_id else None,
                    primary_intent=IntentType(intent_result.intent)
                    if intent_result.intent in IntentType.__members__
                    else IntentType.UNKNOWN,
                )
                self.db.add(conv)
                await self.db.flush()

            # 用户消息
            user_msg = Message(
                conversation_id=conv.id,
                role=MessageRole.USER,
                content=user_message,
                intent=IntentType(intent_result.intent)
                if intent_result.intent in IntentType.__members__
                else IntentType.UNKNOWN,
                intent_confidence=intent_result.confidence,
                prompt_tokens=usage.get("prompt_tokens", 0),
            )
            self.db.add(user_msg)

            # AI 回复
            ai_msg = Message(
                conversation_id=conv.id,
                role=MessageRole.ASSISTANT,
                content=reply,
                rag_sources=rag_sources,
                completion_tokens=usage.get("completion_tokens", 0),
                latency_ms=latency_ms,
            )
            self.db.add(ai_msg)

            # 更新对话统计
            conv.turn_count = (conv.turn_count or 0) + 1
            conv.total_tokens = (conv.total_tokens or 0) + usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)

            await self.db.commit()

        except Exception as e:
            logger.error(f"[Chat] 消息持久化失败: {e}")
            await self.db.rollback()
