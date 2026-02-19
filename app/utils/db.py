from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.utils.config import settings


class Base(DeclarativeBase):
    pass


def _to_async_database_url(url: str) -> str:
    if "+psycopg2" in url:
        return url.replace("+psycopg2", "+asyncpg")
    if "+psycopg" in url:
        return url.replace("+psycopg", "+asyncpg")
    if "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


engine: AsyncEngine = create_async_engine(
    _to_async_database_url(settings.database_url),
    pool_pre_ping=False,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    connect_args={"server_settings": {"timezone": settings.db_timezone}},
)
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=AsyncSession)


async def ensure_tables_exist() -> None:
    # checkfirst=True is the default: creates only missing objects.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db_connection() -> None:
    # Lightweight connectivity probe used during app startup.
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as db:
        yield db
