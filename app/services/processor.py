import asyncio
import logging

from app.utils import db as db_core
from app.utils.enums import TransactionStatus
from app.utils.runtime import get_shutdown_event, register_background_task
from app.utils.time import utcnow
from app.repositories.transaction_repository import TransactionRepository

logger = logging.getLogger(__name__)


def schedule_transaction_processing(transaction_id: str, processing_delay_seconds: int) -> None:
    task = asyncio.create_task(
        process_transaction_background(
            transaction_id=transaction_id,
            processing_delay_seconds=processing_delay_seconds,
        )
    )
    register_background_task(task)

    def _log_task_result(done_task: asyncio.Task) -> None:
        try:
            done_task.result()
        except asyncio.CancelledError:
            # Expected during graceful shutdown task draining.
            return
        except Exception:  # noqa: BLE001
            logger.exception("Background processing task failed. transaction_id=%s", transaction_id)

    task.add_done_callback(_log_task_result)


async def process_transaction_background(
    transaction_id: str, processing_delay_seconds: int, fail_for_testing: bool = False
) -> None:
    shutdown_event = get_shutdown_event()
    async with db_core.SessionLocal() as db:
        repository = TransactionRepository(db)
        transaction = await repository.get_one_by_transaction_id(transaction_id)
        if transaction is None or transaction.status != TransactionStatus.PROCESSING:
            return
        # Stamp start time once so stale retries can be detected.
        await repository.ensure_processing_started(transaction, now=utcnow())

    try:
        try:
            # Wait for either shutdown signal or simulated processing delay.
            await asyncio.wait_for(shutdown_event.wait(), timeout=processing_delay_seconds)
            async with db_core.SessionLocal() as db:
                repository = TransactionRepository(db)
                transaction = await repository.get_one_by_transaction_id(transaction_id)
                if transaction is not None and transaction.status == TransactionStatus.PROCESSING:
                    # Leave row retryable when shutdown interrupts in-flight processing.
                    await repository.mark_interrupted(
                        transaction,
                        message="Processing interrupted by shutdown; eligible for retry",
                    )
            return
        except asyncio.TimeoutError:
            pass

        if fail_for_testing:
            raise RuntimeError("Simulated processing failure")

        async with db_core.SessionLocal() as db:
            repository = TransactionRepository(db)
            transaction = await repository.get_one_by_transaction_id(transaction_id)
            if transaction is None or transaction.status != TransactionStatus.PROCESSING:
                return
            await repository.mark_processed(transaction, processed_at=utcnow())
    except Exception as exc:  # noqa: BLE001
        # Persist failures to avoid silent drops and aid debugging.
        async with db_core.SessionLocal() as db:
            repository = TransactionRepository(db)
            transaction = await repository.get_one_by_transaction_id(transaction_id)
            if transaction is None or transaction.status != TransactionStatus.PROCESSING:
                return
            await repository.mark_failed(transaction, error_message=str(exc))
