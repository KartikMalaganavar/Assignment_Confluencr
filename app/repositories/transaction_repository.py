from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.enums import TransactionStatus
from app.models.transaction import Transaction


class TransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_if_not_exists(
        self,
        *,
        transaction_id: str,
        source_account: str,
        destination_account: str,
        amount: Decimal,
        currency: str,
        status: TransactionStatus,
        processing_started_at: datetime,
        payload_hash: str,
    ) -> str | None:
        # Use INSERT ... ON CONFLICT DO NOTHING for idempotent ingestion.
        insert_stmt = (
            pg_insert(Transaction)
            .values(
                transaction_id=transaction_id,
                source_account=source_account,
                destination_account=destination_account,
                amount=amount,
                currency=currency,
                status=status,
                processing_started_at=processing_started_at,
                payload_hash=payload_hash,
            )
            .on_conflict_do_nothing(index_elements=["transaction_id"])
            .returning(Transaction.transaction_id)
        )
        inserted_transaction_id = (await self.db.execute(insert_stmt)).scalar_one_or_none()
        if inserted_transaction_id is None:
            return None
        await self.db.commit()
        return inserted_transaction_id

    async def get_by_transaction_id(self, transaction_id: str) -> Transaction | None:
        return (await self.db.execute(
            select(Transaction).where(Transaction.transaction_id == transaction_id)
        )).scalar_one_or_none()

    async def record_duplicate_conflict(self, transaction: Transaction, *, now: datetime) -> None:
        transaction.duplicate_conflict_count += 1
        transaction.last_conflict_at = now
        await self.db.commit()


    async def mark_for_retry_if_stale(
        self,
        transaction: Transaction,
        *,
        now: datetime,
        stale_timeout_seconds: int,
    ) -> bool:
        # Only PROCESSING rows without final timestamp are eligible for retry checks.
        if transaction.status != TransactionStatus.PROCESSING or transaction.processed_at is not None:
            return False

        stale_cutoff = now - timedelta(seconds=stale_timeout_seconds)
        # Re-open stuck rows so webhook ingestion can schedule processing again.
        if transaction.processing_started_at is None or transaction.processing_started_at < stale_cutoff:
            transaction.processing_started_at = now
            transaction.error_message = None
            await self.db.commit()
            return True
        return False

    async def ensure_processing_started(self, transaction: Transaction, *, now: datetime) -> None:
        if transaction.processing_started_at is None:
            transaction.processing_started_at = now
            await self.db.commit()

    async def mark_interrupted(self, transaction: Transaction, *, message: str) -> None:
        transaction.processing_started_at = None
        transaction.error_message = message
        await self.db.commit()

    async def mark_processed(self, transaction: Transaction, *, processed_at: datetime) -> None:
        transaction.status = TransactionStatus.PROCESSED
        transaction.processed_at = processed_at
        transaction.error_message = None
        await self.db.commit()

    async def mark_failed(self, transaction: Transaction, *, error_message: str) -> None:
        transaction.status = TransactionStatus.FAILED
        transaction.error_message = error_message
        await self.db.commit()
