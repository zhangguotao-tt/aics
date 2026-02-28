"""
SQLAlchemy 异步数据库连接管理
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings
from utils.logger import logger


# ── 引擎 ──────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# ── Session 工厂 ───────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Base 模型 ──────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── 依赖注入：获取 DB Session ──────────────────────────────
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── 初始化：创建所有表 ──────────────────────────────────────
async def init_db():
    # 导入所有模型以确保 metadata 注册
    from models import user, conversation, knowledge  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库初始化完成，所有表已创建")
