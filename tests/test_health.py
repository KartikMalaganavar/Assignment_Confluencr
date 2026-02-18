from datetime import datetime


def test_health_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "HEALTHY"
    datetime.fromisoformat(payload["current_time"].replace("Z", "+00:00"))
