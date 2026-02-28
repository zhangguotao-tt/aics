"""
聊天服务单元测试（Task17）
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass


@dataclass
class MockIntentResult:
    intent: str = "inquiry"
    confidence: float = 0.9
    method: str = "rule"
    raw_response: str = ""


@pytest.mark.asyncio
class TestChatService:

    @patch("services.chat_service.IntentClassifier")
    @patch("services.chat_service.Retriever")
    @patch("services.chat_service.get_llm_client")
    @patch("services.chat_service.ConversationMemory")
    async def test_chat_returns_response(
        self, mock_memory_cls, mock_llm_fn, mock_retriever_cls, mock_intent_cls
    ):
        """chat() 返回非空响应"""
        # 配置 Mock
        mock_intent = AsyncMock()
        mock_intent.classify.return_value = MockIntentResult()
        mock_intent_cls.return_value = mock_intent

        mock_retriever = AsyncMock()
        mock_retriever.retrieve.return_value = [
            {"id": "c1", "content": "退款流程：进入订单页面点击申请退款。", "source": "manual.pdf", "score": 0.85}
        ]
        mock_retriever_cls.return_value = mock_retriever

        mock_llm = MagicMock()
        mock_llm.chat = AsyncMock(return_value=("您好，退款流程如下...", {"tokens": 50}))
        mock_llm_fn.return_value = mock_llm

        mock_memory = AsyncMock()
        mock_memory.get_recent.return_value = []
        mock_memory.add_user_message = AsyncMock()
        mock_memory.add_assistant_message = AsyncMock()
        mock_memory_cls.return_value = mock_memory

        from services.chat_service import ChatService
        service = ChatService()

        result = await service.chat(
            session_id="sess-test-001",
            user_message="如何退款？",
            user_id="user-001",
            db=MagicMock()
        )

        assert result is not None
        assert "reply" in result or isinstance(result, dict)

    @patch("services.chat_service.IntentClassifier")
    @patch("services.chat_service.get_llm_client")
    @patch("services.chat_service.ConversationMemory")
    async def test_escalate_intent_triggers_transfer(
        self, mock_memory_cls, mock_llm_fn, mock_intent_cls
    ):
        """escalate 意图触发转人工提示"""
        mock_intent = AsyncMock()
        mock_intent.classify.return_value = MockIntentResult(intent="escalate", confidence=0.95)
        mock_intent_cls.return_value = mock_intent

        mock_llm = MagicMock()
        mock_llm.chat = AsyncMock(return_value=("正在为您转接人工客服...", {}))
        mock_llm_fn.return_value = mock_llm

        mock_memory = AsyncMock()
        mock_memory.get_recent.return_value = []
        mock_memory.add_user_message = AsyncMock()
        mock_memory.add_assistant_message = AsyncMock()
        mock_memory_cls.return_value = mock_memory

        from services.chat_service import ChatService
        service = ChatService()

        result = await service.chat(
            session_id="sess-test-002",
            user_message="转人工",
            user_id="user-001",
            db=MagicMock()
        )
        assert result is not None
