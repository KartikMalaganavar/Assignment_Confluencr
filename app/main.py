import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.router.routes_health import router as health_router
from app.router.routes_transactions import router as transactions_router
from app.router.routes_webhooks import router as webhooks_router
from app.utils.config import settings
from app.utils.db import check_db_connection, engine, ensure_tables_exist
from app.utils.logging import configure_logging
from app.utils.runtime import clear_shutdown_signal, drain_background_tasks, set_shutdown_signal
from app.models.transaction import Transaction  # noqa: F401

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    clear_shutdown_signal()
    logger.info("Starting app and validating DB connectivity")
    await asyncio.wait_for(check_db_connection(), timeout=settings.db_operation_timeout_seconds)
    logger.info("Database connection check successful")
    # Always keep schema bootstrapped for local/dev usage when Alembic was not run.
    await ensure_tables_exist()
    logger.info("Schema ensure step completed")
    try:
        yield
    finally:
        set_shutdown_signal()
        await drain_background_tasks()
        # Only close pooled DB connections; this does not drop tables.
        await engine.dispose()


app = FastAPI(title="Confluencr Webhook Processor", lifespan=lifespan)
app.include_router(health_router)
app.include_router(webhooks_router)
app.include_router(transactions_router)
