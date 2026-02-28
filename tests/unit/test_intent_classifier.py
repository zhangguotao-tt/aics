"""
意图识别分类器单元测试（Task17）
"""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
class TestIntentClassifier:

    async def test_rule_match_complaint(self):
        """规则匹配：投诉意图"""
        from core.intent.classifier import IntentClassifier
        clf = IntentClassifier(use_llm_fallback=False)
        result = await clf.classify("这个产品太烂了，我要投诉！")
        assert result.intent == "complaint"
        assert result.confidence > 0.7
        assert result.method == "rule"

    async def test_rule_match_after_sales(self):
        """规则匹配：售后意图"""
        from core.intent.classifier import IntentClassifier
        clf = IntentClassifier(use_llm_fallback=False)
        result = await clf.classify("我想申请退货退款")
        assert result.intent == "after_sales"
        assert result.method == "rule"

    async def test_rule_match_escalate(self):
        """规则匹配：转人工"""
        from core.intent.classifier import IntentClassifier
        clf = IntentClassifier(use_llm_fallback=False)
        result = await clf.classify("我要找人工客服")
        assert result.intent == "escalate"

    async def test_rule_match_chitchat(self):
        """规则匹配：闲聊"""
        from core.intent.classifier import IntentClassifier
        clf = IntentClassifier(use_llm_fallback=False)
        result = await clf.classify("你好，在吗")
        assert result.intent == "chitchat"

    async def test_empty_text(self):
        """空消息处理"""
        from core.intent.classifier import IntentClassifier
        clf = IntentClassifier(use_llm_fallback=False)
        result = await clf.classify("")
        assert result.intent == "unknown"
        assert result.confidence == 0.0

    async def test_parse_llm_response_valid(self):
        """LLM 响应 JSON 解析"""
        from core.intent.classifier import IntentClassifier
        clf = IntentClassifier()
        result = clf._parse_llm_response(
            '{"intent": "inquiry", "confidence": 0.92, "reason": "用户在询问产品功能"}'
        )
        assert result.intent == "inquiry"
        assert result.confidence == 0.92
        assert result.method == "llm"

    async def test_parse_llm_response_invalid(self):
        """LLM 响应解析失败兜底"""
        from core.intent.classifier import IntentClassifier
        clf = IntentClassifier()
        result = clf._parse_llm_response("无法识别的回复内容")
        assert result.intent == "unknown"
        assert result.confidence == 0.3
