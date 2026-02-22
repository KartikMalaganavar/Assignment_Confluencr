import asyncio
import time

from sqlalchemy import select

from app.utils import db as db_core
from app.models.transaction import Transaction


def test_same_payload_duplicate_only_processes_once(client):
    payload = {
        "transaction_id": "txn_same_1",
        "source_account": "acc_user_789",
        "destination_account": "acc_merchant_456",
        "amount": 1500,
        "currency": "INR",
    }
    for _ in range(3):
        response = client.post("/v1/webhooks/transactions", json=payload)
        assert response.status_code == 202

    deadline = time.time() + 10
    while time.time() < deadline:
        query_resp = client.get("/v1/transactions/txn_same_1")
        assert query_resp.status_code == 200
        body = query_resp.json()
        assert isinstance(body, list)
        if body and body[0]["status"] == "PROCESSED":
            break
        time.sleep(0.2)

    async def _assert_db_state() -> None:
        async with db_core.SessionLocal() as db:
            rows = (await db.execute(
                select(Transaction).where(Transaction.transaction_id == "txn_same_1")
            )).scalars().all()
            assert len(rows) == 1
            assert rows[0].duplicate_conflict_count == 0

    asyncio.run(_assert_db_state())
