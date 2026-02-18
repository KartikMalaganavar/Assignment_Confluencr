from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.router.routes_health import router as health_router
from app.router.routes_transactions import router as transactions_router
from app.router.routes_webhooks import router as webhooks_router
from app.utils.db import engine, ensure_tables_exist
from app.utils.logging import configure_logging
from app.utils.runtime import clear_shutdown_signal, set_shutdown_signal
from app.models.transaction import Transaction  # noqa: F401


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    clear_shutdown_signal()
    # Always keep schema bootstrapped for local/dev usage when Alembic was not run.
    ensure_tables_exist()
    try:
        yield
    finally:
        set_shutdown_signal()
        # Only close pooled DB connections; this does not drop tables.
        engine.dispose()


app = FastAPI(title="Confluencr Webhook Processor", lifespan=lifespan)
app.include_router(health_router)
app.include_router(webhooks_router)
app.include_router(transactions_router)
