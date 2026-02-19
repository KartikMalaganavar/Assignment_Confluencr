import asyncio
import time

from sqlalchemy import select

from app.utils import db as db_core
from app.utils.config import settings
from app.models.transaction import Transaction


def test_transaction_gets_processed_after_delay(client):
    settings.processing_delay_seconds = 2
    payload = {
        "transaction_id": "txn_delay_1",
        "source_account": "acc_user_789",
        "destination_account": "acc_merchant_456",
        "amount": 1500,
        "currency": "INR",
    }

    start = time.perf_counter()
    response = client.post("/v1/webhooks/transactions", json=payload)
    assert response.status_code == 202

    deadline = time.time() + 10
    final_status = None
    while time.time() < deadline:
        query_resp = client.get("/v1/transactions/txn_delay_1")
        assert query_resp.status_code == 200
        final_status = query_resp.json()["status"]
        if final_status == "PROCESSED":
            break
        time.sleep(0.2)

    elapsed = time.perf_counter() - start
    if final_status == "FAILED":
        async def _load_error() -> str | None:
            async with db_core.SessionLocal() as db:
                tx = (await db.execute(
                    select(Transaction).where(Transaction.transaction_id == "txn_delay_1")
                )).scalar_one()
                return tx.error_message

        raise AssertionError(f"processing failed: {asyncio.run(_load_error())}")
    assert final_status == "PROCESSED"
    assert elapsed >= 2
