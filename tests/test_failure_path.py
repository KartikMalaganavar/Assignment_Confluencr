import pytest
from sqlalchemy import select

from app.utils import db as db_core
from app.utils.enums import TransactionStatus
from app.models.transaction import Transaction
from app.services.processor import process_transaction_background


@pytest.mark.asyncio
async def test_processing_failure_marks_transaction_failed(test_engine):
    tx = Transaction(
        transaction_id="txn_fail_1",
        source_account="acc_user_1",
        destination_account="acc_merchant_1",
        amount=100,
        currency="INR",
        status=TransactionStatus.PROCESSING,
        payload_hash="abc",
    )
    async with db_core.SessionLocal() as db:
        db.add(tx)
        await db.commit()

    await process_transaction_background(
        transaction_id="txn_fail_1",
        processing_delay_seconds=0,
        fail_for_testing=True,
    )

    async with db_core.SessionLocal() as db:
        updated = (await db.execute(
            select(Transaction).where(Transaction.transaction_id == "txn_fail_1")
        )).scalar_one()
        assert updated.status == TransactionStatus.FAILED
        assert updated.error_message is not None
