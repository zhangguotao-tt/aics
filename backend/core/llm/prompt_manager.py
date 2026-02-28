"""
Prompt 模板管理器

集中管理所有 System Prompt 和 Prompt 模板，支持：
  - 多场景系统提示词（默认客服/投诉/售后等）
  - RAG 上下文注入模板
  - 意图识别 Prompt
  - 动态变量渲染
"""
from string import Template
from typing import Optional


# ── 系统提示词库 ────────────────────────────────────────────
SYSTEM_PROMPTS = {

    "default": """你是一个专业、友善的智能客服助手。

职责：
- 准确回答用户关于产品和服务的问题
- 耐心处理用户的咨询和投诉
- 在知识库中找到相关信息后，给出准确、简洁的回答
- 遇到无法解决的复杂问题，及时引导用户联系人工客服

回答原则：
1. 语言简洁清晰，避免过度专业术语
2. 对用户的情绪表示理解和共情
3. 如果知识库中没有相关信息，诚实告知而不要编造
4. 回答长度适中，重要信息用列表或分段展示

当前日期：{current_date}""",

    "complaint": """你是一个专业的投诉处理专员，具有高度的同理心。

处理投诉时：
1. 首先真诚道歉并表示理解用户的感受
2. 认真倾听并确认问题的具体情况
3. 给出明确的解决方案或处理时间承诺
4. 如果需要，提供补偿方案
5. 确保用户感到被重视和尊重

不要：
- 推卸责任或找借口
- 使用冷漠或机械的回复
- 做出无法兑现的承诺

当前日期：{current_date}""",

    "after_sales": """你是一名专业的售后服务顾问。

你的主要职责：
- 帮助用户处理退换货申请
- 解答产品使用问题
- 协助处理物流和配送问题
- 提供保修政策说明

请根据公司政策给出准确的售后指引，遇到需要人工审核的情况，
请引导用户提交相关凭证并说明处理时效。

当前日期：{current_date}""",

    "chitchat": """你是一个友好的对话助手，可以进行轻松的日常交流。
请保持对话自然、温暖，同时适时引导用户回到业务话题。
当前日期：{current_date}""",
}

# ── RAG 上下文注入模板 ────────────────────────────────────────
RAG_CONTEXT_TEMPLATE = """以下是从知识库中检索到的相关信息，请优先参考这些内容来回答用户问题：

---知识库内容开始---
{context}
---知识库内容结束---

重要提示：
- 如果知识库内容与问题相关，请基于知识库内容回答
- 如果知识库内容不足以回答问题，请诚实告知
- 不要凭空捏造知识库中没有的信息"""

# ── 意图识别 Prompt ───────────────────────────────────────────
INTENT_CLASSIFICATION_PROMPT = """请分析以下用户消息，判断其意图类别。

用户消息："{user_message}"

请从以下类别中选择最合适的一个，并给出置信度（0.0-1.0）：
- chitchat: 闲聊、问候、无关业务的话题
- inquiry: 产品咨询、功能询问、价格查询、政策了解
- complaint: 投诉、不满、批评、差评
- after_sales: 退换货、维修、物流查询、售后问题
- escalate: 明确要求人工客服、紧急问题
- unknown: 无法判断

请严格按照以下 JSON 格式回复，不要包含其他内容：
{{"intent": "<类别>", "confidence": <0.0-1.0>, "reason": "<简短理由>"}}"""

# ── 对话摘要生成 Prompt ───────────────────────────────────────
CONVERSATION_SUMMARY_PROMPT = """请对以下对话内容生成一个简洁的摘要（50字以内），
描述本次对话的主要话题和结果。

对话记录：
{conversation_history}

摘要："""


class PromptManager:
    """Prompt 模板管理器"""

    def get_system_prompt(
        self,
        scene: str = "default",
        current_date: Optional[str] = None,
        extra_vars: Optional[dict] = None,
    ) -> str:
        """
        获取指定场景的系统提示词

        Args:
            scene: 场景名称 (default/complaint/after_sales/chitchat)
            current_date: 当前日期字符串
            extra_vars: 额外变量替换
        """
        from datetime import date
        template_str = SYSTEM_PROMPTS.get(scene, SYSTEM_PROMPTS["default"])
        vars_dict = {"current_date": current_date or date.today().strftime("%Y年%m月%d日")}
        if extra_vars:
            vars_dict.update(extra_vars)
        try:
            return template_str.format(**vars_dict)
        except KeyError:
            return template_str

    def build_rag_system_prompt(
        self,
        scene: str = "default",
        rag_documents: Optional[list[dict]] = None,
    ) -> str:
        """
        构建含 RAG 上下文的完整系统提示词

        Args:
            scene: 场景
            rag_documents: [{"content": "...", "source": "...", "score": 0.9}, ...]
        """
        base_prompt = self.get_system_prompt(scene)

        if not rag_documents:
            return base_prompt

        # 格式化知识库内容
        context_parts = []
        for i, doc in enumerate(rag_documents, 1):
            source = doc.get("source", "未知来源")
            content = doc.get("content", "")
            context_parts.append(f"[{i}] 来源: {source}\n{content}")

        context = "\n\n".join(context_parts)
        rag_section = RAG_CONTEXT_TEMPLATE.format(context=context)

        return f"{base_prompt}\n\n{rag_section}"

    def build_intent_prompt(self, user_message: str) -> str:
        """构建意图识别 Prompt"""
        return INTENT_CLASSIFICATION_PROMPT.format(user_message=user_message)

    def build_summary_prompt(self, conversation_history: str) -> str:
        """构建对话摘要 Prompt"""
        return CONVERSATION_SUMMARY_PROMPT.format(
            conversation_history=conversation_history
        )

    @staticmethod
    def intent_to_scene(intent: str) -> str:
        """将意图类型映射到对应的场景提示词"""
        mapping = {
            "complaint": "complaint",
            "after_sales": "after_sales",
            "chitchat": "chitchat",
        }
        return mapping.get(intent, "default")


# 全局单例
prompt_manager = PromptManager()
