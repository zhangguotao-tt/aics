"""
RAG 检索器

负责：
  - 用户查询向量化
  - 相似度检索 + 分数过滤
  - 结果格式化（含来源信息）
"""
from __future__ import annotations

from typing import Optional

from config import settings
from core.rag.vector_store import get_vector_store
from utils.cache import cache_get, cache_set
from utils.logger import logger


class RAGRetriever:
    """
    RAG 检索器

    Usage:
        retriever = RAGRetriever()
        docs = await retriever.retrieve("如何申请退款？")
    """

    def __init__(
        self,
        top_k: int = None,
        score_threshold: float = None,
    ):
        self.top_k = top_k or settings.rag_top_k
        self.score_threshold = score_threshold or settings.rag_score_threshold
        self._vector_store = get_vector_store()

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[dict] = None,
        use_cache: bool = True,
    ) -> list[dict]:
        """
        检索与查询最相关的知识库文档

        Args:
            query: 用户查询文本
            top_k: 返回文档数（覆盖默认）
            filter_metadata: ChromaDB 元数据过滤条件
            use_cache: 是否缓存检索结果

        Returns:
            [{"content": "...", "source": "...", "score": 0.9, "metadata": {...}}, ...]
        """
        if not query.strip():
            return []

        n = top_k or self.top_k
        cache_key = f"rag:{hash(query.strip())}:{n}"

        # 1. 缓存检查
        if use_cache:
            cached = await cache_get(cache_key)
            if cached is not None:
                logger.debug(f"[RAG] 缓存命中，query={query[:30]}")
                return cached

        # 2. 向量化查询
        from core.llm.client import get_llm_client
        client = get_llm_client()
        query_embedding = await client.embed_text(query)

        # 3. 向量检索
        results = self._vector_store.query(
            query_embeddings=[query_embedding],
            n_results=n,
            where=filter_metadata,
        )

        # 4. 格式化 + 分数过滤
        docs = self._format_results(results)

        # 5. 写缓存（5分钟）
        if use_cache and docs:
            await cache_set(cache_key, docs, ttl=300)

        logger.info(f"[RAG] 检索完成，query='{query[:30]}' 返回 {len(docs)} 个文档")
        return docs

    def _format_results(self, raw_results: dict) -> list[dict]:
        """
        将 ChromaDB 原始结果格式化，并过滤低分文档

        ChromaDB 余弦距离范围 [0, 2]，距离越小越相似
        相似度 = 1 - distance（近似，distance in cosine space）
        """
        docs = []
        if not raw_results or not raw_results.get("ids"):
            return docs

        ids = raw_results["ids"][0]
        documents = raw_results.get("documents", [[]])[0]
        metadatas = raw_results.get("metadatas", [[]])[0]
        distances = raw_results.get("distances", [[]])[0]

        for doc_id, content, meta, dist in zip(ids, documents, metadatas, distances):
            # 余弦距离转相似度得分
            score = max(0.0, 1.0 - dist)
            if score < self.score_threshold:
                continue

            docs.append({
                "id": doc_id,
                "content": content,
                "source": meta.get("source", meta.get("title", "知识库")),
                "score": round(score, 4),
                "metadata": meta,
            })

        # 按相似度降序排列
        docs.sort(key=lambda x: x["score"], reverse=True)
        return docs


# 全局单例
rag_retriever = RAGRetriever()
