"""
LLM 统一客户端

支持三种提供商，通过 LLM_PROVIDER 环境变量切换，业务代码零改动：
  - openai      : OpenAI GPT-4o / GPT-4o-mini
  - ollama      : 本地 Ollama（Qwen / Llama / Mistral 等）
  - azure_openai: Azure OpenAI Service
"""
from __future__ import annotations

import time
from functools import lru_cache
from typing import AsyncIterator, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.outputs import ChatResult

from config import settings
from utils.logger import logger


def _build_llm() -> BaseChatModel:
    """根据配置构建对应的 LLM 实例"""
    provider = settings.llm_provider

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        logger.info(f"使用 OpenAI 模型: {settings.openai_chat_model}")
        return ChatOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
            model=settings.openai_chat_model,
            max_tokens=settings.openai_max_tokens,
            temperature=settings.openai_temperature,
            streaming=True,
        )

    elif provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        logger.info(f"使用 Ollama 本地模型: {settings.ollama_model}")
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=settings.openai_temperature,
            streaming=True,
        )

    elif provider == "azure_openai":
        from langchain_openai import AzureChatOpenAI
        logger.info(f"使用 Azure OpenAI: {settings.azure_openai_deployment_name}")
        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=settings.azure_openai_deployment_name,
            api_version=settings.azure_openai_api_version,
            api_key=settings.azure_openai_api_key,
            temperature=settings.openai_temperature,
            streaming=True,
        )

    raise ValueError(f"不支持的 LLM 提供商: {provider}")


def _build_embedding_model():
    """根据配置构建 Embedding 模型"""
    provider = settings.llm_provider

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
            model=settings.openai_embedding_model,
        )

    elif provider == "ollama":
        from langchain_community.embeddings import OllamaEmbeddings
        return OllamaEmbeddings(
            base_url=settings.ollama_base_url,
            model="nomic-embed-text",  # Ollama 推荐的嵌入模型
        )

    elif provider == "azure_openai":
        from langchain_openai import AzureOpenAIEmbeddings
        return AzureOpenAIEmbeddings(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    raise ValueError(f"不支持的提供商: {provider}")


class LLMClient:
    """LLM 统一客户端，封装调用/流式/统计逻辑"""

    def __init__(self):
        self._llm: BaseChatModel = _build_llm()
        self._embedding = _build_embedding_model()
        logger.info(f"LLMClient 初始化完成 [provider={settings.llm_provider}]")

    @property
    def llm(self) -> BaseChatModel:
        return self._llm

    @property
    def embedding(self):
        return self._embedding

    # ── 普通调用 ────────────────────────────────────────────
    async def chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
    ) -> tuple[str, dict]:
        """
        发送消息并等待完整回复。

        Args:
            messages: [{"role": "user"/"assistant", "content": "..."}]
            system_prompt: 系统提示词（覆盖默认）

        Returns:
            (回复文本, 统计信息)
        """
        lc_messages = self._convert_messages(messages, system_prompt)
        start = time.time()

        result: ChatResult = await self._llm.ainvoke(lc_messages)

        elapsed_ms = int((time.time() - start) * 1000)
        content = result.content

        usage = {}
        if hasattr(result, "response_metadata"):
            meta = result.response_metadata
            usage = {
                "prompt_tokens": meta.get("token_usage", {}).get("prompt_tokens", 0),
                "completion_tokens": meta.get("token_usage", {}).get("completion_tokens", 0),
                "latency_ms": elapsed_ms,
            }

        logger.debug(f"LLM 回复完成 [{elapsed_ms}ms] tokens={usage}")
        return content, usage

    # ── 流式调用 ────────────────────────────────────────────
    async def stream_chat(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        流式输出，逐 Token yield。

        Usage:
            async for token in client.stream_chat(messages):
                print(token, end="", flush=True)
        """
        lc_messages = self._convert_messages(messages, system_prompt)

        async for chunk in self._llm.astream(lc_messages):
            if chunk.content:
                yield chunk.content

    # ── 文本向量化 ──────────────────────────────────────────
    async def embed_text(self, text: str) -> list[float]:
        """将文本向量化"""
        return await self._embedding.aembed_query(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量向量化文档"""
        return await self._embedding.aembed_documents(texts)

    # ── 内部工具 ────────────────────────────────────────────
    @staticmethod
    def _convert_messages(
        messages: list[dict],
        system_prompt: Optional[str],
    ) -> list[BaseMessage]:
        """将 dict 消息格式转换为 LangChain BaseMessage"""
        lc_messages: list[BaseMessage] = []

        if system_prompt:
            lc_messages.append(SystemMessage(content=system_prompt))

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))

        return lc_messages


@lru_cache()
def get_llm_client() -> LLMClient:
    """获取 LLMClient 单例"""
    return LLMClient()
