from fastapi.testclient import TestClient
from pwdlib import PasswordHash

from app.main import app


def test_private_documents_require_login():
    client = TestClient(app)

    response = client.get("/api/documents")

    assert response.status_code == 401


def test_private_rag_requires_login():
    client = TestClient(app)

    response = client.post(
        "/api/agent/ask",
        json={"question": "What is in my documents?"},
    )

    assert response.status_code == 401


def test_login_and_logout(monkeypatch):
    hashed = PasswordHash.recommended().hash(
        "test-only-password"
    )
    monkeypatch.setenv(
        "CONTEXTIQ_ADMIN_PASSWORD_HASH",
        hashed,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"password": "test-only-password"},
        )
        assert response.status_code == 200

        response = client.get("/api/auth/me")
        assert response.status_code == 200

        response = client.post("/api/auth/logout")
        assert response.status_code == 200

        response = client.get("/api/documents")
        assert response.status_code == 401