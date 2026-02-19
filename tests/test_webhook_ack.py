import time

from app.utils.config import settings


def test_webhook_ack_is_202_and_fast(client):
    payload = {
        "transaction_id": "txn_ack_1",
        "source_account": "acc_user_789",
        "destination_account": "acc_merchant_456",
        "amount": 1500,
        "currency": "INR",
    }
    start = time.perf_counter()
    response = client.post("/v1/webhooks/transactions", json=payload)
    elapsed = time.perf_counter() - start

    assert response.status_code == 202
    assert response.json()["acknowledged"] is True
    assert response.json()["response_time_ms"] >= 0
    # TestClient waits for BackgroundTasks to complete, unlike a real network client.
    assert elapsed < (settings.processing_delay_seconds + 1.0)
