"""
全局配置管理
使用 pydantic-settings 从环境变量或 .env 文件加载配置
"""
from functools import lru_cache
from typing import List, Literal
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── 应用基础 ───────────────────────────────────────────
    app_name: str = "LLM智能客服系统"
    app_env: Literal["development", "production", "testing"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    secret_key: str = "change-this-secret-key-in-production"

    # ── JWT ────────────────────────────────────────────────
    jwt_secret_key: str = "change-this-jwt-secret-key-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # ── LLM ───────────────────────────────────────────────
    llm_provider: Literal["openai", "ollama", "azure_openai"] = "openai"

    # OpenAI
    openai_api_key: str = ""
    openai_api_base: str = "https://api.openai.com/v1"
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_max_tokens: int = 2048
    openai_temperature: float = 0.7

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    # Azure OpenAI
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment_name: str = ""
    azure_openai_api_version: str = "2024-02-01"

    # ── 数据库 ─────────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "cs_user"
    postgres_password: str = "cs_password"
    postgres_db: str = "customer_service"
    database_url: str = "postgresql+asyncpg://cs_user:cs_password@localhost:5432/customer_service"

    # ── Redis ──────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_conversation: int = 3600
    cache_ttl_knowledge: int = 86400

    # ── ChromaDB ───────────────────────────────────────────
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection_name: str = "knowledge_base"

    # ── RAG ────────────────────────────────────────────────
    rag_top_k: int = 5
    rag_score_threshold: float = 0.5
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50

    # ── 对话 ───────────────────────────────────────────────
    max_history_turns: int = 10
    max_context_tokens: int = 4000

    # ── 限流 ───────────────────────────────────────────────
    rate_limit_per_minute: int = 60
    rate_limit_per_user: int = 20

    # ── 日志 ───────────────────────────────────────────────
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"

    # ── CORS ───────────────────────────────────────────────
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @computed_field
    @property
    def active_llm_model(self) -> str:
        """返回当前激活的 LLM 模型名称"""
        if self.llm_provider == "ollama":
            return self.ollama_model
        elif self.llm_provider == "azure_openai":
            return self.azure_openai_deployment_name
        return self.openai_chat_model


@lru_cache()
def get_settings() -> Settings:
    """获取全局配置单例（带缓存）"""
    return Settings()


# 全局配置实例
settings = get_settings()
