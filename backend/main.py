"""
FastAPI 应用入口

包含：
  - 中间件：CORS / 限流 / 请求日志
  - 路由：REST（认证/对话/知识库/管理）+ WebSocket 流式对话
  - 生命周期：DB / Redis / ChromaDB 初始化
  - 全局异常处理
"""
from __future__ import annotations

import json
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from config import settings
from db.database import init_db
from utils.logger import logger, setup_logger
from utils.cache import init_redis
from api.routes import chat, auth, knowledge, admin
from api.middleware.rate_limit import RateLimitMiddleware


# ── 生命周期管理 ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭时的生命周期钩子"""
    setup_logger()
    logger.info(f"🚀 {settings.app_name} 启动 [env={settings.app_env}, llm={settings.llm_provider}]")
    if settings.llm_provider == "deepseek":
        k = (settings.dashscope_api_key or "").strip()
        if k:
            logger.info(f"千问 Embedding: DASHSCOPE_API_KEY 已加载 (sk-...{k[-4:] if len(k) >= 4 else '****'})")
        else:
            logger.warning("千问 Embedding: DASHSCOPE_API_KEY 未设置，RAG 调用将报 401")

    await init_redis()
    await init_db()

    # 初始化 ChromaDB
    from core.rag.vector_store import get_vector_store
    get_vector_store()

    logger.info("✅ 所有服务就绪，开始接受请求")
    yield
    logger.info("🛑 应用关闭")


# ── 应用初始化 ──────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description="基于 LLM 的智能客服系统 API",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── 中间件注册 ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RateLimitMiddleware)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """请求日志中间件"""
    req_id = str(uuid.uuid4())[:8]
    start = time.time()
    logger.info(f"[{req_id}] → {request.method} {request.url.path}")
    response = await call_next(request)
    elapsed = int((time.time() - start) * 1000)
    logger.info(f"[{req_id}] ← {response.status_code} [{elapsed}ms]")
    return response


# ── 全局异常处理 ────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "服务器内部错误，请稍后重试"},
    )


# ── REST 路由注册 ───────────────────────────────────────────
app.include_router(auth.router,      prefix="/api", tags=["认证"])
app.include_router(chat.router,      prefix="/api", tags=["对话"])
app.include_router(knowledge.router, prefix="/api", tags=["知识库"])
app.include_router(admin.router,     prefix="/api", tags=["管理"])


# ── WebSocket：流式对话 ─────────────────────────────────────
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket 流式对话端点

    客户端发送: {"message": "...", "token": "<可选JWT>"}
    服务端推送:
      {"type": "token",  "content": "..."}   逐 Token
      {"type": "done",   "session_id": "..."} 完成
      {"type": "error",  "detail": "..."}     错误
    """
    await websocket.accept()
    logger.info(f"[WS] 新连接 session={session_id[:8]}")

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            user_message = data.get("message", "").strip()
            jwt_token = data.get("token")

            # 可选 JWT 认证
            user_id = None
            if jwt_token:
                try:
                    from services.auth_service import AuthService
                    payload = AuthService.verify_token(jwt_token)
                    user_id = payload.get("sub")
                except ValueError:
                    pass

            if not user_message:
                await websocket.send_json({"type": "error", "detail": "消息不能为空"})
                continue

            from db.database import AsyncSessionLocal
            from services.chat_service import ChatService
            async with AsyncSessionLocal() as db:
                svc = ChatService(db)
                try:
                    async for chunk in svc.stream_chat(
                        user_message=user_message,
                        session_id=session_id,
                        user_id=user_id,
                    ):
                        await websocket.send_json({"type": "token", "content": chunk})
                    await websocket.send_json({"type": "done", "session_id": session_id})
                except Exception as e:
                    logger.error(f"[WS] 推理异常: {e}")
                    await websocket.send_json({"type": "error", "detail": str(e)})

    except WebSocketDisconnect:
        logger.info(f"[WS] 连接断开 session={session_id[:8]}")
    except Exception as e:
        logger.error(f"[WS] 意外异常: {e}")


# ── 系统端点 ────────────────────────────────────────────────
@app.get("/health", tags=["系统"])
async def health_check():
    from utils.cache import get_redis
    redis_ok = False
    try:
        r = get_redis()
        if r:
            await r.ping()
            redis_ok = True
    except Exception:
        pass
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "llm_provider": settings.llm_provider,
        "redis": "connected" if redis_ok else "disconnected",
    }


@app.get("/", tags=["系统"])
async def root():
    return {"message": f"欢迎使用 {settings.app_name}", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )
