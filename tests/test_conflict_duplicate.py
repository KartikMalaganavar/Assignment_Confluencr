from sqlalchemy import select

from app.utils import db as db_core
from app.models.transaction import Transaction


def test_conflicting_duplicate_keeps_original_and_tracks_conflict(client):
    payload_1 = {
        "transaction_id": "txn_conflict_1",
        "source_account": "acc_user_789",
        "destination_account": "acc_merchant_456",
        "amount": 1500,
        "currency": "INR",
    }
    payload_2 = {
        "transaction_id": "txn_conflict_1",
        "source_account": "acc_user_789",
        "destination_account": "acc_merchant_456",
        "amount": 1600,
        "currency": "INR",
    }

    response_1 = client.post("/v1/webhooks/transactions", json=payload_1)
    response_2 = client.post("/v1/webhooks/transactions", json=payload_2)
    assert response_1.status_code == 202
    assert response_2.status_code == 202

    with db_core.SessionLocal() as db:
        tx = db.execute(
            select(Transaction).where(Transaction.transaction_id == "txn_conflict_1")
        ).scalar_one()
        assert float(tx.amount) == 1500.0
        assert tx.duplicate_conflict_count == 1
        assert tx.last_conflict_at is not None
