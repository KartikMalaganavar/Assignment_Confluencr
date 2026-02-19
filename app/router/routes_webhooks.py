import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from time import perf_counter_ns

from app.utils.config import settings
from app.utils.db import get_db
from app.dto.webhook import TransactionWebhookAck, TransactionWebhookIn
from app.services.processor import schedule_transaction_processing
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


def get_service(db: AsyncSession = Depends(get_db)) -> WebhookService:
    return WebhookService(db)


@router.post(
    "/transactions",
    response_model=TransactionWebhookAck,
    status_code=status.HTTP_202_ACCEPTED,
)
async def receive_transaction_webhook(
    payload: TransactionWebhookIn,
    service: WebhookService = Depends(get_service),
) -> TransactionWebhookAck:
    started_ns = perf_counter_ns()
    try:
        transaction_id, should_schedule = await asyncio.wait_for(
            service.ingest_transaction_webhook(payload),
            timeout=settings.db_operation_timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        logger.exception("Webhook ingest timed out")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database operation timed out") from exc
    except SQLAlchemyError as exc:
        logger.exception("Webhook ingest DB error")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable") from exc

    if should_schedule:
        # Fire-and-forget scheduling keeps webhook ACK independent from long processing.
        schedule_transaction_processing(
            transaction_id=transaction_id,
            processing_delay_seconds=settings.processing_delay_seconds,
        )

    elapsed_ms = (perf_counter_ns() - started_ns) / 1_000_000
    return TransactionWebhookAck(
        transaction_id=transaction_id,
        status_code=202,
        response_time_ms=round(elapsed_ms, 3),
    )
