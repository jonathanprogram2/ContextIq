from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "contextiq-api"}


def test_ready_schema(monkeypatch):
    monkeypatch.setattr("app.main.check_database", lambda: "ok")
    monkeypatch.setattr("app.main.check_blob", lambda: "ok")
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
