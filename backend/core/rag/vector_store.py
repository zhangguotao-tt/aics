"""
ChromaDB 向量存储管理

负责：
  - 初始化/加载 ChromaDB collection
  - 文档向量化存储
  - 相似度检索
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings
from utils.logger import logger


class VectorStore:
    """ChromaDB 向量数据库管理器"""

    def __init__(self):
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection = None
        self._initialized = False

    def initialize(self) -> None:
        """初始化 ChromaDB（同步，在应用启动时调用）"""
        if self._initialized:
            return
        try:
            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"hnsw:space": "cosine"},  # 使用余弦相似度
            )
            self._initialized = True
            count = self._collection.count()
            logger.info(
                f"ChromaDB 初始化完成，集合: {settings.chroma_collection_name}，"
                f"已有向量: {count}"
            )
        except Exception as e:
            logger.error(f"ChromaDB 初始化失败: {e}")
            raise

    @property
    def collection(self):
        if not self._initialized:
            self.initialize()
        return self._collection

    # ── 添加文档 ─────────────────────────────────────────────
    def add_documents(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: Optional[list[dict]] = None,
    ) -> None:
        """批量添加文档向量"""
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas or [{} for _ in ids],
        )
        logger.info(f"已添加 {len(ids)} 个向量到知识库")

    # ── 相似度检索 ────────────────────────────────────────────
    def query(
        self,
        query_embeddings: list[list[float]],
        n_results: int = None,
        where: Optional[dict] = None,
    ) -> dict:
        """
        向量相似度检索

        Returns:
            chromadb 查询结果字典
        """
        n = n_results or settings.rag_top_k
        kwargs = {
            "query_embeddings": query_embeddings,
            "n_results": min(n, self.collection.count() or 1),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        return self.collection.query(**kwargs)

    # ── 删除文档 ─────────────────────────────────────────────
    def delete_by_ids(self, ids: list[str]) -> None:
        """按 ID 删除向量"""
        self.collection.delete(ids=ids)
        logger.info(f"已删除 {len(ids)} 个向量")

    def delete_by_metadata(self, where: dict) -> None:
        """按元数据条件删除（如删除某篇文档的所有分块）"""
        self.collection.delete(where=where)

    # ── 统计 ─────────────────────────────────────────────────
    def count(self) -> int:
        return self.collection.count()


@lru_cache()
def get_vector_store() -> VectorStore:
    store = VectorStore()
    store.initialize()
    return store
