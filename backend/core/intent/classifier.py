"""
意图识别分类器

采用两阶段策略：
  1. 规则匹配（快速，无需 LLM 调用）
  2. LLM 分类（精准，用于规则无法覆盖的情况）
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from utils.cache import cache_get, cache_set
from utils.logger import logger


@dataclass
class IntentResult:
    intent: str          # 意图类别
    confidence: float    # 置信度 0.0-1.0
    reason: str          # 判断理由
    method: str          # 判断方式: "rule" | "llm"


# ── 规则字典 ──────────────────────────────────────────────────
# 格式: {intent: [关键词列表]}
RULE_PATTERNS: dict[str, list[str]] = {
    "escalate": [
        "人工", "转人工", "人工客服", "真人", "人工服务",
        "call center", "电话客服", "要投诉你们",
    ],
    "complaint": [
        "投诉", "举报", "太差了", "太烂了", "骗人", "诈骗",
        "气死了", "太坑了", "垃圾", "要退款", "维权",
        "不满意", "很失望", "失望透顶",
    ],
    "after_sales": [
        "退款", "退货", "换货", "维修", "售后", "保修",
        "快递", "物流", "发货", "包裹", "签收", "破损",
        "坏了", "不好用", "无法使用", "故障",
    ],
    "inquiry": [
        "怎么", "如何", "可以", "能不能", "多少钱", "价格",
        "费用", "什么时候", "在哪", "怎样", "咨询", "了解",
        "介绍", "是否", "支持", "功能",
    ],
    "chitchat": [
        "你好", "hi", "hello", "在吗", "谢谢", "感谢",
        "再见", "拜拜", "bye", "哈哈", "哦哦", "好的",
        "知道了", "明白了",
    ],
}

# 置信度阈值：规则匹配的默认置信度
RULE_CONFIDENCE = 0.85


class IntentClassifier:
    """
    意图识别分类器

    Usage:
        classifier = IntentClassifier()
        result = await classifier.classify("我要退货")
        print(result.intent)  # "after_sales"
    """

    def __init__(self, use_llm_fallback: bool = True):
        self.use_llm_fallback = use_llm_fallback
        self._llm_client = None  # 懒加载，避免循环导入

    async def classify(
        self,
        text: str,
        use_cache: bool = True,
    ) -> IntentResult:
        """
        对用户消息进行意图分类

        Args:
            text: 用户消息文本
            use_cache: 是否使用缓存（相同文本复用结果）

        Returns:
            IntentResult
        """
        if not text or not text.strip():
            return IntentResult("unknown", 0.0, "空消息", "rule")

        # 1. 检查缓存
        if use_cache:
            cache_key = f"intent:{hash(text.strip())}"
            cached = await cache_get(cache_key)
            if cached:
                logger.debug(f"[Intent] 缓存命中: {cached['intent']}")
                return IntentResult(**cached)

        # 2. 规则匹配（快速路径）
        rule_result = self._rule_match(text)
        if rule_result:
            if use_cache:
                await cache_set(cache_key, vars(rule_result), ttl=300)
            logger.debug(f"[Intent] 规则匹配: {rule_result.intent} ({rule_result.confidence:.2f})")
            return rule_result

        # 3. LLM 分类（精准路径）
        if self.use_llm_fallback:
            llm_result = await self._llm_classify(text)
            if use_cache:
                await cache_set(cache_key, vars(llm_result), ttl=300)
            logger.debug(f"[Intent] LLM分类: {llm_result.intent} ({llm_result.confidence:.2f})")
            return llm_result

        return IntentResult("unknown", 0.3, "无法识别意图", "rule")

    # ── 规则匹配 ──────────────────────────────────────────────
    def _rule_match(self, text: str) -> Optional[IntentResult]:
        """基于关键词规则的快速意图匹配"""
        text_lower = text.lower()
        best_intent = None
        best_score = 0

        for intent, keywords in RULE_PATTERNS.items():
            # 计算命中关键词数量
            hits = sum(1 for kw in keywords if kw in text_lower)
            if hits > best_score:
                best_score = hits
                best_intent = intent

        if best_intent and best_score >= 1:
            # 命中越多关键词，置信度越高（最高 0.95）
            confidence = min(0.75 + best_score * 0.05, 0.95)
            return IntentResult(
                intent=best_intent,
                confidence=confidence,
                reason=f"规则匹配 {best_score} 个关键词",
                method="rule",
            )
        return None

    # ── LLM 分类 ─────────────────────────────────────────────
    async def _llm_classify(self, text: str) -> IntentResult:
        """使用 LLM 进行精准意图分类"""
        try:
            from core.llm.client import get_llm_client
            from core.llm.prompt_manager import prompt_manager

            client = get_llm_client()
            prompt = prompt_manager.build_intent_prompt(text)

            response, _ = await client.chat(
                messages=[{"role": "user", "content": prompt}]
            )

            # 解析 JSON 响应
            result = self._parse_llm_response(response)
            return result

        except Exception as e:
            logger.error(f"[Intent] LLM 分类失败: {e}")
            return IntentResult("inquiry", 0.5, "LLM分类失败，默认咨询", "rule")

    @staticmethod
    def _parse_llm_response(response: str) -> IntentResult:
        """解析 LLM 返回的 JSON 意图结果"""
        try:
            # 提取 JSON 部分（防止 LLM 在 JSON 前后添加文字）
            json_match = re.search(r'\{[^{}]+\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return IntentResult(
                    intent=data.get("intent", "unknown"),
                    confidence=float(data.get("confidence", 0.7)),
                    reason=data.get("reason", ""),
                    method="llm",
                )
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[Intent] JSON 解析失败: {e}, 原始回复: {response[:100]}")

        return IntentResult("unknown", 0.3, "LLM响应解析失败", "llm")


# 全局单例
intent_classifier = IntentClassifier()
