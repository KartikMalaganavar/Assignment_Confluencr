def test_get_transaction_not_found(client):
    response = client.get("/v1/transactions/txn_missing")
    assert response.status_code == 200
    assert response.json() == []


def test_invalid_payload_rejected(client):
    payload = {
        "transaction_id": "txn_invalid_1",
        "source_account": "acc_user_789",
        "destination_account": "acc_merchant_456",
        "amount": -1,
        "currency": "INR",
    }
    response = client.post("/v1/webhooks/transactions", json=payload)
    assert response.status_code == 422
