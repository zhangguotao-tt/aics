"""
对话上下文记忆管理

策略：
  1. 活跃对话缓存在 Redis（TTL 1小时），快速读写
  2. 采用滑动窗口：保留最近 MAX_HISTORY_TURNS 轮
  3. Token 超限时自动裁剪最早消息
  4. 所有消息永久存储在 PostgreSQL
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

from config import settings
from utils.cache import cache_get, cache_set, cache_delete
from utils.logger import logger


class ConversationMemory:
    """
    对话记忆管理器（基于 Redis 的滑动窗口）

    消息格式：
      {"role": "user"|"assistant"|"system", "content": "..."}
    """

    def __init__(
        self,
        session_id: str,
        max_turns: int = None,
        ttl: int = None,
    ):
        self.session_id = session_id
        self.max_turns = max_turns or settings.max_history_turns
        self.ttl = ttl or settings.cache_ttl_conversation
        self._cache_key = f"conv_memory:{session_id}"
        # 内存 fallback（Redis 不可用时使用）
        self._local_cache: list[dict] = []

    # ── 读取历史 ─────────────────────────────────────────────
    async def get_history(self) -> list[dict]:
        """获取当前对话历史（最近 N 轮）"""
        cached = await cache_get(self._cache_key)
        if cached is not None:
            return cached

        # Redis 未命中，返回内存缓存
        return self._local_cache.copy()

    # ── 添加消息 ─────────────────────────────────────────────
    async def add_message(self, role: str, content: str) -> None:
        """添加一条消息到记忆"""
        history = await self.get_history()
        history.append({"role": role, "content": content})

        # 滑动窗口：最多保留 max_turns 轮（1轮 = user + assistant 两条）
        max_messages = self.max_turns * 2
        if len(history) > max_messages:
            # 保留尾部最新消息
            history = history[-max_messages:]
            logger.debug(f"[Memory] 裁剪对话历史到 {max_messages} 条 [{self.session_id}]")

        await self._save(history)

    async def add_user_message(self, content: str) -> None:
        await self.add_message("user", content)

    async def add_assistant_message(self, content: str) -> None:
        await self.add_message("assistant", content)

    # ── 获取最近 N 轮 ─────────────────────────────────────────
    async def get_recent(self, n_turns: int = None) -> list[dict]:
        """获取最近 n 轮对话（用于构建 Prompt）"""
        n = (n_turns or self.max_turns) * 2
        history = await self.get_history()
        return history[-n:] if len(history) > n else history

    # ── 清除记忆 ─────────────────────────────────────────────
    async def clear(self) -> None:
        """清空当前会话记忆（对话结束时调用）"""
        await cache_delete(self._cache_key)
        self._local_cache.clear()
        logger.info(f"[Memory] 会话记忆已清除 [{self.session_id}]")

    # ── 格式化为文本 ─────────────────────────────────────────
    async def format_history_text(self) -> str:
        """将历史格式化为纯文本（用于摘要生成）"""
        history = await self.get_history()
        lines = []
        for msg in history:
            role_name = "用户" if msg["role"] == "user" else "客服"
            lines.append(f"{role_name}: {msg['content']}")
        return "\n".join(lines)

    # ── 内部：持久化到 Redis ──────────────────────────────────
    async def _save(self, history: list[dict]) -> None:
        self._local_cache = history.copy()
        success = await cache_set(self._cache_key, history, ttl=self.ttl)
        if not success:
            logger.warning(f"[Memory] Redis 写入失败，使用内存缓存 [{self.session_id}]")

    # ── 工厂方法 ─────────────────────────────────────────────
    @classmethod
    def from_session(cls, session_id: Optional[str] = None) -> "ConversationMemory":
        """从 session_id 创建记忆实例（None 时自动生成）"""
        sid = session_id or str(uuid.uuid4())
        return cls(session_id=sid)
