from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from time import perf_counter_ns

from app.utils.config import settings
from app.utils.db import get_db
from app.dto.webhook import TransactionWebhookAck, TransactionWebhookIn
from app.services.processor import process_transaction_background
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


def get_service(db: Session = Depends(get_db)) -> WebhookService:
    return WebhookService(db)


@router.post(
    "/transactions",
    response_model=TransactionWebhookAck,
    status_code=status.HTTP_202_ACCEPTED,
)
def receive_transaction_webhook(
    payload: TransactionWebhookIn,
    background_tasks: BackgroundTasks,
    service: WebhookService = Depends(get_service),
) -> TransactionWebhookAck:
    started_ns = perf_counter_ns()
    try:
        transaction_id, should_schedule = service.ingest_transaction_webhook(payload)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable") from exc

    if should_schedule:
        # Schedule async processing after immediate 202 acknowledgement.
        background_tasks.add_task(
            process_transaction_background,
            transaction_id=transaction_id,
            processing_delay_seconds=settings.processing_delay_seconds,
        )

    elapsed_ms = (perf_counter_ns() - started_ns) / 1_000_000
    return TransactionWebhookAck(
        transaction_id=transaction_id,
        status_code=202,
        response_time_ms=round(elapsed_ms, 3),
    )
