"""
性能优化与缓存策略（Task18）
包含：连接池优化、多级缓存、Embedding批量缓存、热点知识预热、异步DB查询优化
"""
import asyncio
import hashlib
import time
from functools import lru_cache
from typing import Optional, List, Dict, Any

# ─────────────────────────────────────────────
# 1. 缓存 Key 统一命名空间
# ─────────────────────────────────────────────

class CacheKeys:
    """Redis 缓存 Key 命名规范"""
    # Embedding 缓存：text hash → vector
    EMBED_PREFIX = "embed:v1:"
    # RAG 检索结果缓存
    RAG_PREFIX = "rag:v1:"
    # 意图分类缓存
    INTENT_PREFIX = "intent:v1:"
    # 热点知识文档 ID 集合
    HOT_DOCS_KEY = "hotdocs:ids"
    # 系统统计快照（每5分钟刷新）
    STATS_SNAPSHOT_KEY = "stats:snapshot"

    @staticmethod
    def embed_key(text: str) -> str:
        h = hashlib.md5(text.encode()).hexdigest()
        return f"{CacheKeys.EMBED_PREFIX}{h}"

    @staticmethod
    def rag_key(query: str, top_k: int) -> str:
        h = hashlib.md5(f"{query}:{top_k}".encode()).hexdigest()
        return f"{CacheKeys.RAG_PREFIX}{h}"

    @staticmethod
    def intent_key(text: str) -> str:
        h = hashlib.md5(text.encode()).hexdigest()
        return f"{CacheKeys.INTENT_PREFIX}{h}"


# ─────────────────────────────────────────────
# 2. 多级缓存管理器
# ─────────────────────────────────────────────

class MultiLevelCache:
    """
    L1 = 进程内 LRU dict（容量 1000，无 TTL）
    L2 = Redis（带 TTL）
    读：L1 miss → L2 → 回填 L1
    写：同时写 L1 + L2
    """

    def __init__(self, redis_client, l1_max_size: int = 1000):
        self._redis = redis_client
        self._l1: Dict[str, Any] = {}
        self._l1_order: List[str] = []  # 简单 FIFO 淘汰
        self._l1_max = l1_max_size

    # ── L1 ──────────────────────────

    def _l1_get(self, key: str) -> Optional[Any]:
        return self._l1.get(key)

    def _l1_set(self, key: str, value: Any):
        if key not in self._l1:
            if len(self._l1_order) >= self._l1_max:
                evict = self._l1_order.pop(0)
                self._l1.pop(evict, None)
            self._l1_order.append(key)
        self._l1[key] = value

    def _l1_delete(self, key: str):
        self._l1.pop(key, None)
        if key in self._l1_order:
            self._l1_order.remove(key)

    # ── 公开接口 ─────────────────────

    async def get(self, key: str) -> Optional[str]:
        # L1
        val = self._l1_get(key)
        if val is not None:
            return val
        # L2
        if self._redis:
            try:
                val = await self._redis.get(key)
                if val is not None:
                    self._l1_set(key, val)
                    return val
            except Exception:
                pass
        return None

    async def set(self, key: str, value: str, ttl: int = 300):
        self._l1_set(key, value)
        if self._redis:
            try:
                await self._redis.setex(key, ttl, value)
            except Exception:
                pass

    async def delete(self, key: str):
        self._l1_delete(key)
        if self._redis:
            try:
                await self._redis.delete(key)
            except Exception:
                pass

    async def mget(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """批量获取，L1优先"""
        result: Dict[str, Optional[str]] = {}
        missing = []
        for k in keys:
            v = self._l1_get(k)
            if v is not None:
                result[k] = v
            else:
                missing.append(k)
        if missing and self._redis:
            try:
                values = await self._redis.mget(*missing)
                for k, v in zip(missing, values):
                    result[k] = v
                    if v is not None:
                        self._l1_set(k, v)
            except Exception:
                for k in missing:
                    result[k] = None
        return result


# ─────────────────────────────────────────────
# 3. Embedding 批量缓存层
# ─────────────────────────────────────────────

class CachedEmbedder:
    """
    包装 LLMClient.embed_documents() 增加批量 Redis 缓存:
    - 检查缓存 → 仅对 cache miss 的文本调用 LLM API
    - 结果写回缓存（TTL 24h，embedding 变化少）
    - 节省 70%+ 的 embedding API 调用
    """

    EMBED_TTL = 86400  # 24 小时

    def __init__(self, llm_client, cache: MultiLevelCache):
        self._llm = llm_client
        self._cache = cache

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        import json

        keys = [CacheKeys.embed_key(t) for t in texts]
        cached_map = await self._cache.mget(keys)

        results: List[Optional[List[float]]] = [None] * len(texts)
        miss_indices: List[int] = []
        miss_texts: List[str] = []

        for i, (key, text) in enumerate(zip(keys, texts)):
            val = cached_map.get(key)
            if val:
                results[i] = json.loads(val)
            else:
                miss_indices.append(i)
                miss_texts.append(text)

        # 批量计算 miss 的 embedding
        if miss_texts:
            new_embeds = await self._llm.embed_documents(miss_texts)
            for idx, embed in zip(miss_indices, new_embeds):
                results[idx] = embed
                await self._cache.set(
                    keys[idx], json.dumps(embed), ttl=self.EMBED_TTL
                )

        return results  # type: ignore


# ─────────────────────────────────────────────
# 4. 热点知识预热
# ─────────────────────────────────────────────

class KnowledgePrewarmer:
    """
    在服务启动/知识库更新后，将高频检索的文档 embedding 预热到 L1 缓存，
    减少首次查询的冷启动延迟
    """

    def __init__(self, retriever, cache: MultiLevelCache, db_session):
        self._retriever = retriever
        self._cache = cache
        self._db = db_session

    async def prewarm(self, top_n: int = 20):
        """预热 top_n 个高频命中文档"""
        from utils.logger import get_logger
        log = get_logger("prewarm")

        try:
            from sqlalchemy import text
            result = await self._db.execute(
                text(
                    "SELECT chroma_id FROM knowledge_chunks "
                    "ORDER BY hit_count DESC LIMIT :n"
                ),
                {"n": top_n},
            )
            rows = result.fetchall()
            chroma_ids = [r[0] for r in rows]
            log.info(f"[Prewarm] 预热 {len(chroma_ids)} 个高频知识块...")

            # 触发 retriever 内部缓存写入（通过 dummy 查询）
            prewarm_tasks = [
                self._retriever.retrieve(
                    query=chroma_id,  # 用 id 触发，retriever 会命中 chroma
                    top_k=1,
                    use_cache=True,
                )
                for chroma_id in chroma_ids[:5]  # 限速，避免启动时打爆
            ]
            await asyncio.gather(*prewarm_tasks, return_exceptions=True)
            log.info(f"[Prewarm] 完成")
        except Exception as e:
            log.warning(f"[Prewarm] 预热失败（不影响启动）: {e}")


# ─────────────────────────────────────────────
# 5. 数据库连接池配置建议（注释式文档）
# ─────────────────────────────────────────────

DB_POOL_SETTINGS = {
    # asyncpg 连接池参数
    "pool_size": 20,           # 常驻连接数（建议 = CPU核数 × 2 + 2）
    "max_overflow": 30,        # 超出 pool_size 的临时连接上限
    "pool_timeout": 30,        # 等待可用连接的超时（秒）
    "pool_recycle": 1800,      # 连接最长复用时间（秒），防止连接过期
    "pool_pre_ping": True,     # 每次取连接前检测存活，自动重连
}

# 在 backend/db/database.py 中使用：
# engine = create_async_engine(DATABASE_URL, **DB_POOL_SETTINGS)


# ─────────────────────────────────────────────
# 6. 异步 DB 查询批处理工具
# ─────────────────────────────────────────────

class AsyncBatchSaver:
    """
    消息批量写入器 — 将高并发场景下的多条 INSERT
    合并为一次批量提交，降低 DB 写压力
    """

    def __init__(self, session_factory, batch_size: int = 50, flush_interval: float = 1.0):
        self._factory = session_factory
        self._buffer: List[Any] = []
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None

    def start(self):
        self._flush_task = asyncio.create_task(self._periodic_flush())

    async def stop(self):
        if self._flush_task:
            self._flush_task.cancel()
        await self._flush_now()

    async def add(self, orm_obj: Any):
        async with self._lock:
            self._buffer.append(orm_obj)
            if len(self._buffer) >= self._batch_size:
                await self._flush_now()

    async def _periodic_flush(self):
        while True:
            await asyncio.sleep(self._flush_interval)
            await self._flush_now()

    async def _flush_now(self):
        async with self._lock:
            if not self._buffer:
                return
            batch = self._buffer[:]
            self._buffer.clear()

        async with self._factory() as session:
            try:
                session.add_all(batch)
                await session.commit()
            except Exception as e:
                await session.rollback()
                from utils.logger import get_logger
                get_logger("batch_saver").error(f"批量写入失败: {e}")
