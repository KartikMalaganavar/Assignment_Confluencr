from sqlalchemy.orm import Session

from app.utils.config import settings
from app.utils.enums import TransactionStatus
from app.utils.time import utcnow
from app.dto.webhook import TransactionWebhookIn
from app.models.transaction import Transaction
from app.repositories.transaction_repository import TransactionRepository
from app.utils.idempotency import payload_hash

import logging
logger = logging.getLogger(__name__)


class WebhookService:
    def __init__(self, db: Session):
        self.repository = TransactionRepository(db)

    def ingest_transaction_webhook(self, payload: TransactionWebhookIn) -> tuple[Transaction, bool]:
        # Hashing lets us distinguish true duplicates from conflicting duplicates.
        payload_digest = payload_hash(payload)
        now = utcnow()

        # First delivery wins: insert once by unique transaction_id.
        created = self.repository.create_if_not_exists(
            transaction_id=payload.transaction_id,
            source_account=payload.source_account,
            destination_account=payload.destination_account,
            amount=payload.amount,
            currency=payload.currency,
            status=TransactionStatus.PROCESSING,
            processing_started_at=now,
            payload_hash=payload_digest,
        )
        if created is not None:
            return created, True

        existing = self.repository.get_by_transaction_id(payload.transaction_id)
        if existing is None:
            raise RuntimeError("transaction disappeared after conflict check")

        if existing.payload_hash != payload_digest:
            logger.warning(
                "Received webhook with duplicate transaction_id but different payload. "
                "transaction_id=%s existing_payload_hash=%s new_payload_hash=%s",
                payload.transaction_id,
                existing.payload_hash,
                payload_digest,
            )
            # Do not overwrite original payload; only track conflict metadata.
            self.repository.record_duplicate_conflict(existing, now=now)

        # Re-queue only if the row is stale and still in PROCESSING state.
        should_schedule = self.repository.mark_for_retry_if_stale(
            existing,
            now=now,
            stale_timeout_seconds=settings.processing_stale_timeout_seconds,
        )
        return existing, should_schedule
