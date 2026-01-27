# File: backend/tests/api/test_health.py
# Purpose: Validate health check endpoint behavior.


def test_health_check(app_client):
    response = app_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "macjarvis-backend"
