#!/usr/bin/env python3
"""
知识库批量导入脚本（Task20）
将 data/knowledge/ 目录下的文档批量向量化并导入 ChromaDB
用法：python scripts/load_knowledge.py [--dir data/knowledge] [--clear]
"""
import asyncio
import argparse
import sys
from pathlib import Path

# 将 backend 目录加入 Python 路径（本机：项目根/backend；容器内：/app 即 backend 根）
_backend_root = Path(__file__).resolve().parent.parent / "backend"
if _backend_root.exists():
    sys.path.insert(0, str(_backend_root))
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def load_knowledge(knowledge_dir: str, clear_existing: bool = False):
    from config import get_settings
    from db.database import init_db, AsyncSessionLocal
    from core.rag.embedder import DocumentEmbedder
    from core.rag.vector_store import get_vector_store
    from models.knowledge import KnowledgeDocument, DocumentStatus
    from utils.logger import setup_logging, get_logger

    setup_logging()
    log = get_logger("load_knowledge")
    settings = get_settings()

    # 初始化数据库
    await init_db()

    doc_dir = Path(knowledge_dir)
    if not doc_dir.exists():
        log.error(f"目录不存在: {doc_dir}")
        sys.exit(1)

    # 支持的文件类型
    supported = {".pdf", ".docx", ".txt", ".md"}
    files = [f for f in doc_dir.iterdir() if f.suffix.lower() in supported]

    if not files:
        log.warning(f"目录 {doc_dir} 中没有找到支持的文档（PDF/DOCX/TXT/MD）")
        return

    log.info(f"发现 {len(files)} 个文档，开始导入...")

    if clear_existing:
        vs = get_vector_store()
        collection = vs.collection
        log.warning(f"⚠️  清空现有知识库（共 {collection.count()} 条向量）")
        vs._client.delete_collection(settings.chroma_collection_name)
        vs._collection = None
        vs._initialized = False
        log.info("知识库已清空")

    embedder = DocumentEmbedder()
    success, failed = 0, 0

    async with AsyncSessionLocal() as session:
        for file_path in files:
            log.info(f"处理: {file_path.name}")
            try:
                # 创建 DB 记录（模型字段：title 必填，file_path/file_size/description/status）
                doc = KnowledgeDocument(
                    title=file_path.name,
                    file_path=str(file_path),
                    file_size=file_path.stat().st_size,
                    status=DocumentStatus.PROCESSING,
                    description=f"批量导入: {file_path.name}",
                )
                session.add(doc)
                await session.flush()

                # 解析文件为文本，再向量化（embed_document 参数：content, doc_id, source）
                content = DocumentEmbedder.parse_file(str(file_path))
                doc.file_hash = DocumentEmbedder.compute_hash(content)
                chunk_records = await embedder.embed_document(
                    content=content,
                    doc_id=str(doc.id),
                    source=file_path.name,
                )

                # 更新状态
                doc.status = DocumentStatus.ACTIVE
                doc.chunk_count = len(chunk_records)
                await session.commit()

                log.info(
                    f"  ✅ {file_path.name} → {doc.chunk_count} 个知识块"
                )
                success += 1

            except Exception as e:
                await session.rollback()
                log.error(f"  ❌ {file_path.name} 失败: {type(e).__name__}: {e}")
                # 补充 HTTP/API 错误详情（OpenAI、requests 等）
                if hasattr(e, "response") and e.response is not None:
                    try:
                        body = getattr(e.response, "text", None) or getattr(e.response, "content", None)
                        if body is not None:
                            body = body if isinstance(body, str) else (body.decode("utf-8", errors="replace")[:500])
                        status = getattr(e.response, "status_code", None)
                        log.error(f"  响应状态: {status}, 响应体: {body}")
                    except Exception:
                        pass
                if "404" in str(e):
                    log.error(
                        "  千问 Embedding 404 排查：1) 容器内需传入 DASHSCOPE_API_KEY / DASHSCOPE_EMBEDDING_MODEL；"
                        "2) 可尝试 .env 中改为 DASHSCOPE_EMBEDDING_MODEL=text-embedding-v2；"
                        "3) 确认 docker-compose 中 LLM_PROVIDER=deepseek 且已挂载 ./backend:/app"
                    )
                log.exception("详细异常")
                failed += 1

    log.info(f"\n导入完成：成功 {success} 个，失败 {failed} 个")


def main():
    parser = argparse.ArgumentParser(description="知识库批量导入工具")
    parser.add_argument(
        "--dir",
        default="data/knowledge",
        help="知识文档目录（默认: data/knowledge）",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="导入前清空现有知识库",
    )
    args = parser.parse_args()
    asyncio.run(load_knowledge(args.dir, args.clear))


if __name__ == "__main__":
    main()
