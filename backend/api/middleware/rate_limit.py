"""
限流中间件（基于 Redis 滑动窗口）
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from utils.cache import get_redis
from utils.logger import logger
from config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    基于 Redis 的 IP + 用户双维度限流

    全局限流：每 IP 每分钟最多 rate_limit_per_minute 次
    用户限流：每用户每分钟最多 rate_limit_per_user 次（在路由层通过 header 获取）
    """

    async def dispatch(self, request: Request, call_next):
        # 跳过健康检查
        if request.url.path in ("/health", "/", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        redis_client = get_redis()
        if not redis_client:
            # Redis 不可用时跳过限流
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:ip:{ip}"

        try:
            count = await redis_client.incr(key)
            if count == 1:
                await redis_client.expire(key, 60)  # 60秒窗口

            if count > settings.rate_limit_per_minute:
                logger.warning(f"[RateLimit] IP {ip} 超过限流阈值 ({count}次/分)")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"请求过于频繁，请 {60} 秒后重试",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[RateLimit] 限流检查失败: {e}")

        return await call_next(request)
