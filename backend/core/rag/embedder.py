"""
文档分块与向量化处理器

负责：
  - 多格式文档解析（PDF/Word/TXT/Markdown）
  - 文本分块（RecursiveCharacterTextSplitter）
  - 批量向量化并存入 ChromaDB
  - PostgreSQL 元数据记录
"""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter

from config import settings
from core.rag.vector_store import get_vector_store
from utils.logger import logger


class DocumentEmbedder:
    """
    文档嵌入处理器

    Usage:
        embedder = DocumentEmbedder()
        chunks = await embedder.embed_document(
            content="文档内容...",
            doc_id="uuid",
            source="产品手册v1.0",
        )
    """

    def __init__(self):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
            length_function=len,
        )
        self._vector_store = get_vector_store()

    # ── 核心：文档分块 + 向量化 ──────────────────────────────
    async def embed_document(
        self,
        content: str,
        doc_id: str,
        source: str = "知识库",
        extra_metadata: Optional[dict] = None,
    ) -> list[dict]:
        """
        将文档内容分块并向量化存入 ChromaDB

        Args:
            content: 文档全文
            doc_id: 文档唯一ID（对应 PostgreSQL knowledge_documents.id）
            source: 文档名称/来源（展示给用户）
            extra_metadata: 额外元数据

        Returns:
            分块记录列表 [{"chroma_id": ..., "content": ..., "index": ...}]
        """
        if not content.strip():
            logger.warning(f"[Embedder] 文档内容为空，跳过: {doc_id}")
            return []

        # 1. 文本分块
        chunks = self._splitter.split_text(content)
        logger.info(f"[Embedder] 文档 {doc_id[:8]} 分块完成，共 {len(chunks)} 块")

        # 2. 批量向量化
        from core.llm.client import get_llm_client
        client = get_llm_client()
        embeddings = await client.embed_documents(chunks)

        # 3. 准备 ChromaDB 数据
        chroma_ids = []
        metadatas = []
        chunk_records = []

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chroma_id = f"{doc_id}_{i}"
            meta = {
                "doc_id": str(doc_id),
                "source": source,
                "chunk_index": i,
                "title": source,
                **(extra_metadata or {}),
            }
            chroma_ids.append(chroma_id)
            metadatas.append(meta)
            chunk_records.append({
                "chroma_id": chroma_id,
                "content": chunk,
                "index": i,
                "char_start": content.find(chunk),
            })

        # 4. 存入 ChromaDB
        self._vector_store.add_documents(
            ids=chroma_ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

        logger.info(f"[Embedder] 文档 {doc_id[:8]} 向量化完成，{len(chunks)} 个向量已存储")
        return chunk_records

    # ── 文件解析 ─────────────────────────────────────────────
    @staticmethod
    def parse_file(file_path: str) -> str:
        """解析不同格式的文件，返回纯文本"""
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return DocumentEmbedder._parse_pdf(file_path)
        elif suffix in (".docx", ".doc"):
            return DocumentEmbedder._parse_word(file_path)
        elif suffix in (".md", ".markdown"):
            return DocumentEmbedder._parse_markdown(file_path)
        else:
            # 默认按 UTF-8 文本读取
            return path.read_text(encoding="utf-8")

    @staticmethod
    def _parse_pdf(file_path: str) -> str:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    @staticmethod
    def _parse_word(file_path: str) -> str:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(para.text for para in doc.paragraphs if para.text)

    @staticmethod
    def _parse_markdown(file_path: str) -> str:
        import markdown
        from bs4 import BeautifulSoup
        text = Path(file_path).read_text(encoding="utf-8")
        html = markdown.markdown(text)
        return BeautifulSoup(html, "html.parser").get_text()

    @staticmethod
    def compute_hash(content: str) -> str:
        """计算内容 SHA-256 哈希（文档去重）"""
        return hashlib.sha256(content.encode()).hexdigest()

    # ── 删除文档向量 ─────────────────────────────────────────
    def delete_document(self, doc_id: str) -> None:
        """删除指定文档的所有向量"""
        self._vector_store.delete_by_metadata({"doc_id": str(doc_id)})
        logger.info(f"[Embedder] 文档 {doc_id[:8]} 的向量已全部删除")


# 全局单例
document_embedder = DocumentEmbedder()
