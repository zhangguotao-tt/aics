"""
对话记忆模块单元测试（Task17）
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
class TestConversationMemory:

    async def test_add_and_get_messages(self):
        """添加消息后可正确获取"""
        from core.memory.conversation_memory import ConversationMemory
        mem = ConversationMemory("test-session-001", use_redis=False)
        await mem.add_user_message("你好")
        await mem.add_assistant_message("您好，请问有什么可以帮助您？")
        messages = await mem.get_recent(10)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "你好"
        assert messages[1]["role"] == "assistant"

    async def test_sliding_window(self):
        """超出窗口大小后自动截断"""
        from core.memory.conversation_memory import ConversationMemory
        mem = ConversationMemory("test-session-002", use_redis=False, max_turns=3)
        for i in range(5):
            await mem.add_user_message(f"用户消息{i}")
            await mem.add_assistant_message(f"助手回复{i}")
        messages = await mem.get_recent(20)
        # max_turns=3 means keep last 3 *turns* = 6 messages
        assert len(messages) <= 6

    async def test_clear_memory(self):
        """清空记忆"""
        from core.memory.conversation_memory import ConversationMemory
        mem = ConversationMemory("test-session-003", use_redis=False)
        await mem.add_user_message("消息1")
        await mem.add_assistant_message("回复1")
        await mem.clear()
        messages = await mem.get_recent(10)
        assert messages == []

    async def test_format_history_text(self):
        """格式化历史对话为文本"""
        from core.memory.conversation_memory import ConversationMemory
        mem = ConversationMemory("test-session-004", use_redis=False)
        await mem.add_user_message("请问如何退款？")
        await mem.add_assistant_message("您可以在订单页面申请退款。")
        text = await mem.format_history_text()
        assert "用户" in text or "User" in text or "请问如何退款" in text
        assert "退款" in text

    async def test_get_recent_n_turns(self):
        """get_recent 按轮次截取"""
        from core.memory.conversation_memory import ConversationMemory
        mem = ConversationMemory("test-session-005", use_redis=False)
        for i in range(4):
            await mem.add_user_message(f"Q{i}")
            await mem.add_assistant_message(f"A{i}")
        messages = await mem.get_recent(2)
        # 最近 2 条
        assert len(messages) == 2
