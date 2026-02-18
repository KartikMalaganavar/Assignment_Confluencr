import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.utils import db as db_core
from app.utils.config import settings
from app.models.transaction import Transaction  # noqa: F401

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/confluencr",
)


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    db_core.engine = engine
    db_core.SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    settings.database_url = TEST_DATABASE_URL
    return engine


@pytest.fixture(autouse=True)
def setup_database(test_engine):
    db_core.Base.metadata.drop_all(bind=test_engine)
    db_core.Base.metadata.create_all(bind=test_engine)
    yield
    db_core.Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    settings.db_auto_create = False
    settings.processing_delay_seconds = 1
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
