import time

from app.utils.config import settings


def test_webhook_ack_under_processing_load(client):
    warmup_payload = {
        "transaction_id": "txn_load_warmup",
        "source_account": "acc_user_1",
        "destination_account": "acc_merchant_1",
        "amount": 100,
        "currency": "INR",
    }
    assert client.post("/v1/webhooks/transactions", json=warmup_payload).status_code == 202

    latencies = []
    for i in range(20):
        payload = {
            "transaction_id": f"txn_load_{i}",
            "source_account": "acc_user_789",
            "destination_account": "acc_merchant_456",
            "amount": 1500 + i,
            "currency": "INR",
        }
        start = time.perf_counter()
        response = client.post("/v1/webhooks/transactions", json=payload)
        latencies.append(time.perf_counter() - start)
        assert response.status_code == 202

    p95_index = max(int(len(latencies) * 0.95) - 1, 0)
    p95 = sorted(latencies)[p95_index]
    # In TestClient, each request waits for the task completion.
    assert p95 < (settings.processing_delay_seconds + 0.5)
