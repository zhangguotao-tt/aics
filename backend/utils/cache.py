"""Redis 缓存工具"""
import json
from typing import Any, Optional
import redis.asyncio as redis
from config import settings
from utils.logger import logger

_redis_client: Optional[redis.Redis] = None


async def init_redis():
    global _redis_client
    try:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        await _redis_client.ping()
        logger.info("Redis 连接成功")
    except Exception as e:
        logger.warning(f"Redis 连接失败，将使用内存缓存: {e}")
        _redis_client = None


def get_redis() -> Optional[redis.Redis]:
    return _redis_client


async def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    if not _redis_client:
        return False
    try:
        await _redis_client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        return True
    except Exception as e:
        logger.error(f"缓存写入失败 [{key}]: {e}")
        return False


async def cache_get(key: str) -> Optional[Any]:
    if not _redis_client:
        return None
    try:
        data = await _redis_client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.error(f"缓存读取失败 [{key}]: {e}")
        return None


async def cache_delete(key: str) -> bool:
    if not _redis_client:
        return False
    try:
        await _redis_client.delete(key)
        return True
    except Exception as e:
        logger.error(f"缓存删除失败 [{key}]: {e}")
        return False
