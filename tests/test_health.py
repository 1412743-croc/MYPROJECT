from fastapi.testclient import TestClient

from app.main import app


def test_health_check_returns_up() -> None:
    client = TestClient(app)

    response = client.get("/actuator/health")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}
