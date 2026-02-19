import asyncio
import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.utils import db as db_core
from app.utils.config import settings
from app.models.transaction import Transaction  # noqa: F401

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/confluencr",
)


@pytest.fixture(scope="session")
def test_engine():
    # NullPool avoids cross-event-loop connection reuse in Windows test runs.
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True, poolclass=NullPool)
    db_core.engine = engine
    db_core.SessionLocal = async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    settings.database_url = TEST_DATABASE_URL
    return engine


@pytest.fixture(autouse=True)
def setup_database(test_engine):
    async def _setup() -> None:
        async with test_engine.begin() as conn:
            await conn.run_sync(db_core.Base.metadata.drop_all)
            await conn.run_sync(db_core.Base.metadata.create_all)

    async def _teardown() -> None:
        async with test_engine.begin() as conn:
            await conn.run_sync(db_core.Base.metadata.drop_all)

    asyncio.run(_setup())
    yield
    asyncio.run(_teardown())
    asyncio.run(test_engine.dispose())


@pytest.fixture
def client():
    settings.db_auto_create = False
    settings.processing_delay_seconds = 1
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
