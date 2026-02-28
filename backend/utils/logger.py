"""
结构化日志与追踪系统（Task16）
基于 loguru，支持 request_id 传播、LLM调用追踪、对话审计日志
"""
import sys
import uuid
import time
import functools
import json
import datetime
from typing import Optional, Callable
from loguru import logger

# ─────────────────────────────────────────────
# 全局日志配置
# ─────────────────────────────────────────────

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level:<8}</level> | "
    "<cyan>{extra[request_id]}</cyan> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "{message}"
)

# 给所有 logger 设置 request_id 默认值，避免 KeyError
logger = logger.bind(request_id="system")


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = "logs/app.log"):
    """初始化结构化日志配置（兼容原 setup_logger 接口）"""
    try:
        from config import settings
        log_level = getattr(settings, "log_level", log_level)
        log_file = getattr(settings, "log_file", log_file)
    except Exception:
        pass

    logger.remove()

    # 控制台输出（带 request_id 占位）
    logger.add(
        sys.stdout,
        format=LOG_FORMAT,
        level=log_level,
        colorize=True,
        enqueue=True,
    )

    # 文件输出（按天轮转）
    if log_file:
        logger.add(
            log_file,
            format=LOG_FORMAT,
            level=log_level,
            rotation="00:00",
            retention="30 days",
            compression="zip",
            encoding="utf-8",
            enqueue=True,
        )

    # 独立错误日志
    logger.add(
        "logs/errors.log",
        format=LOG_FORMAT,
        level="ERROR",
        rotation="100 MB",
        retention="90 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
    )

    logger.bind(request_id="system").info(
        f"日志系统初始化完成，级别: {log_level}, 文件: {log_file}"
    )
    return logger


# 保持向后兼容
def setup_logger():
    return setup_logging()


# ─────────────────────────────────────────────
# Request ID 上下文
# ─────────────────────────────────────────────

class RequestContext:
    """请求 ID 上下文（协程安全，基于 contextvars 可进一步扩展）"""
    _current_id: str = "system"

    @classmethod
    def set(cls, request_id: str):
        cls._current_id = request_id

    @classmethod
    def get(cls) -> str:
        return cls._current_id

    @classmethod
    def generate(cls) -> str:
        rid = str(uuid.uuid4())[:8]
        cls.set(rid)
        return rid


def get_logger(name: str = "app"):
    """获取绑定了 request_id 的 logger 实例"""
    return logger.bind(request_id=RequestContext.get())


# ─────────────────────────────────────────────
# LLM 调用追踪装饰器
# ─────────────────────────────────────────────

def trace_llm_call(func: Callable) -> Callable:
    """
    装饰 LLM 异步调用方法，自动记录:
    - 消息数量 / prompt 字符数
    - 耗时（毫秒）
    - Token 消耗
    - 异常信息
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        log = get_logger("llm.trace")
        request_id = RequestContext.get()
        start_ts = time.perf_counter()

        messages = kwargs.get("messages", args[1] if len(args) > 1 else [])
        msg_count = len(messages) if isinstance(messages, list) else 0
        prompt_len = sum(len(str(m.get("content", ""))) for m in messages) if msg_count else 0

        log.info(
            f"[LLM START] func={func.__name__} "
            f"msg_count={msg_count} prompt_chars={prompt_len} req_id={request_id}"
        )
        try:
            result = await func(*args, **kwargs)
            elapsed_ms = int((time.perf_counter() - start_ts) * 1000)
            if isinstance(result, tuple) and len(result) == 2:
                content, usage = result
                tokens = usage.get("total_tokens", "?") if isinstance(usage, dict) else "?"
            else:
                content, tokens = result, "?"
            log.info(
                f"[LLM END] func={func.__name__} "
                f"elapsed={elapsed_ms}ms tokens={tokens} "
                f"reply_chars={len(str(content))} req_id={request_id}"
            )
            return result
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start_ts) * 1000)
            log.error(
                f"[LLM ERROR] func={func.__name__} "
                f"elapsed={elapsed_ms}ms error={type(exc).__name__}: {exc} "
                f"req_id={request_id}"
            )
            raise

    return wrapper


# ─────────────────────────────────────────────
# 对话审计日志
# ─────────────────────────────────────────────

class ConversationAuditLogger:
    """
    对话审计日志 — 以 JSON Lines 格式记录完整对话事件，
    用于合规审计与质量回溯（保留 180 天）
    """

    def __init__(self):
        self._audit = logger.bind(request_id="audit")
        # 独立的审计日志文件
        logger.add(
            "logs/audit_conversations.jsonl",
            format="{message}",
            level="INFO",
            rotation="1 day",
            retention="180 days",
            filter=lambda r: r["extra"].get("request_id") == "audit",
            encoding="utf-8",
        )

    def _emit(self, event: dict):
        event.setdefault("ts", datetime.datetime.utcnow().isoformat())
        self._audit.info(json.dumps(event, ensure_ascii=False))

    def log_conversation_start(self, session_id: str, user_id: Optional[str], ip: str):
        self._emit({
            "event": "conversation_start",
            "session_id": session_id,
            "user_id": user_id or "guest",
            "ip": ip,
        })

    def log_message_received(
        self, session_id: str, user_id: Optional[str],
        message: str, intent: str, intent_conf: float
    ):
        self._emit({
            "event": "message_received",
            "session_id": session_id,
            "user_id": user_id or "guest",
            "message_preview": message[:100],
            "intent": intent,
            "intent_confidence": round(intent_conf, 3),
        })

    def log_reply_sent(self, session_id: str, latency_ms: int, rag_hit: bool, tokens: int):
        self._emit({
            "event": "reply_sent",
            "session_id": session_id,
            "latency_ms": latency_ms,
            "rag_hit": rag_hit,
            "tokens": tokens,
        })

    def log_conversation_end(self, session_id: str, turn_count: int, total_tokens: int):
        self._emit({
            "event": "conversation_end",
            "session_id": session_id,
            "turn_count": turn_count,
            "total_tokens": total_tokens,
        })


# ─────────────────────────────────────────────
# 单例
# ─────────────────────────────────────────────

_audit_logger_instance: Optional[ConversationAuditLogger] = None


def get_audit_logger() -> ConversationAuditLogger:
    global _audit_logger_instance
    if _audit_logger_instance is None:
        _audit_logger_instance = ConversationAuditLogger()
    return _audit_logger_instance
