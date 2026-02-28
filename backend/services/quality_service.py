"""
对话质量评估服务（Task15）

指标：
  - 意图识别准确率统计
  - 回复延迟分布（P50/P95）
  - 知识库命中率
  - 用户满意度（基于反馈）
  - 对话完成率
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.conversation import Message, Conversation, MessageFeedback, IntentType
from utils.logger import logger


class QualityEvaluator:
    """对话质量评估器"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_overall_metrics(self, days: int = 7) -> dict:
        """
        获取最近 N 天的整体质量指标

        Returns:
            {
                "period_days": 7,
                "total_conversations": 100,
                "total_messages": 450,
                "avg_turns_per_conv": 4.5,
                "avg_latency_ms": 1200,
                "p95_latency_ms": 3500,
                "rag_hit_rate": 0.72,
                "avg_satisfaction": 4.2,
                "intent_distribution": {...},
                "helpful_rate": 0.85,
            }
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # 总对话数
        total_convs = await self.db.scalar(
            select(func.count()).select_from(Conversation)
            .where(Conversation.started_at >= since)
        ) or 0

        # 总消息数
        total_msgs = await self.db.scalar(
            select(func.count()).select_from(Message)
            .where(Message.created_at >= since)
        ) or 0

        # 平均回复延迟（只统计 AI 消息）
        latency_stats = await self.db.execute(
            select(
                func.avg(Message.latency_ms).label("avg"),
                func.percentile_cont(0.95).within_group(Message.latency_ms).label("p95"),
            ).where(
                and_(Message.created_at >= since, Message.latency_ms.isnot(None))
            )
        )
        lat = latency_stats.one()

        # RAG 命中率（rag_sources 非空的比率）
        ai_msgs_total = await self.db.scalar(
            select(func.count()).select_from(Message)
            .where(and_(Message.created_at >= since, Message.role == "assistant"))
        ) or 1
        rag_hit = await self.db.scalar(
            select(func.count()).select_from(Message)
            .where(and_(
                Message.created_at >= since,
                Message.role == "assistant",
                Message.rag_sources != [],
            ))
        ) or 0

        # 意图分布
        intent_result = await self.db.execute(
            select(Message.intent, func.count().label("cnt"))
            .where(Message.created_at >= since)
            .group_by(Message.intent)
        )
        intent_dist = {row.intent.value: row.cnt for row in intent_result if row.intent}

        # 用户满意度（反馈评分均值）
        avg_rating = await self.db.scalar(
            select(func.avg(MessageFeedback.rating))
            .where(MessageFeedback.created_at >= since)
        )

        # 点赞率
        total_fb = await self.db.scalar(
            select(func.count()).select_from(MessageFeedback)
            .where(and_(MessageFeedback.created_at >= since, MessageFeedback.is_helpful.isnot(None)))
        ) or 1
        helpful_count = await self.db.scalar(
            select(func.count()).select_from(MessageFeedback)
            .where(and_(MessageFeedback.created_at >= since, MessageFeedback.is_helpful == True))
        ) or 0

        return {
            "period_days": days,
            "total_conversations": total_convs,
            "total_messages": total_msgs,
            "avg_turns_per_conv": round(total_msgs / max(total_convs, 1) / 2, 1),
            "avg_latency_ms": round(lat.avg or 0),
            "p95_latency_ms": round(lat.p95 or 0),
            "rag_hit_rate": round(rag_hit / ai_msgs_total, 3),
            "avg_satisfaction": round(float(avg_rating or 0), 2),
            "intent_distribution": intent_dist,
            "helpful_rate": round(helpful_count / total_fb, 3),
        }

    async def get_low_quality_conversations(self, limit: int = 10) -> list[dict]:
        """获取质量较低的对话（延迟高/评分低）用于人工审查"""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.avg_satisfaction < 3)
            .order_by(Conversation.started_at.desc())
            .limit(limit)
        )
        convs = result.scalars().all()
        return [
            {
                "session_id": c.session_id,
                "intent": c.primary_intent.value,
                "turn_count": c.turn_count,
                "avg_satisfaction": c.avg_satisfaction,
                "started_at": c.started_at.isoformat(),
            } for c in convs
        ]
