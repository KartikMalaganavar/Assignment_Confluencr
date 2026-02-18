import asyncio

from app.utils import db as db_core
from app.utils.enums import TransactionStatus
from app.utils.runtime import get_shutdown_event
from app.utils.time import utcnow
from app.repositories.transaction_repository import TransactionRepository


async def process_transaction_background(
    transaction_id: str, processing_delay_seconds: int, fail_for_testing: bool = False
) -> None:
    shutdown_event = get_shutdown_event()
    with db_core.SessionLocal() as db:
        repository = TransactionRepository(db)
        transaction = repository.get_by_transaction_id(transaction_id)
        if transaction is None or transaction.status != TransactionStatus.PROCESSING:
            return
        # Stamp start time once so stale retries can be detected.
        repository.ensure_processing_started(transaction, now=utcnow())

    try:
        try:
            # Wait for either shutdown signal or simulated processing delay.
            await asyncio.wait_for(shutdown_event.wait(), timeout=processing_delay_seconds)
            with db_core.SessionLocal() as db:
                repository = TransactionRepository(db)
                transaction = repository.get_by_transaction_id(transaction_id)
                if transaction is not None and transaction.status == TransactionStatus.PROCESSING:
                    # Leave row retryable when shutdown interrupts in-flight processing.
                    repository.mark_interrupted(
                        transaction,
                        message="Processing interrupted by shutdown; eligible for retry",
                    )
            return
        except asyncio.TimeoutError:
            pass

        if fail_for_testing:
            raise RuntimeError("Simulated processing failure")

        with db_core.SessionLocal() as db:
            repository = TransactionRepository(db)
            transaction = repository.get_by_transaction_id(transaction_id)
            if transaction is None or transaction.status != TransactionStatus.PROCESSING:
                return
            repository.mark_processed(transaction, processed_at=utcnow())
    except Exception as exc:  # noqa: BLE001
        # Persist failures to avoid silent drops and aid debugging.
        with db_core.SessionLocal() as db:
            repository = TransactionRepository(db)
            transaction = repository.get_by_transaction_id(transaction_id)
            if transaction is None or transaction.status != TransactionStatus.PROCESSING:
                return
            repository.mark_failed(transaction, error_message=str(exc))
