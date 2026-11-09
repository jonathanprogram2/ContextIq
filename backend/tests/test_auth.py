"""Database-backed authentication and session tests."""

from uuid import UUID

from fastapi.testclient import TestClient
from pwdlib import PasswordHash

from app import auth
from app.main import app

USER_ID = UUID("11111111-1111-4111-8111-111111111111")


def fake_user(password="test-only-password", version=1):
    return {
        "id": USER_ID,
        "username": "testuser",
        "password_hash": PasswordHash.recommended().hash(password),
        "role": "user",
        "session_version": version,
    }


def test_private_documents_require_login():
    with TestClient(app) as client:
        response = client.get("/api/documents")

    assert response.status_code == 401


def test_private_rag_requires_login():
    with TestClient(app) as client:
        response = client.post(
            "/api/agent/ask",
            json={"question": "What is in my documents?"},
        )

    assert response.status_code == 401


def test_database_login_and_logout(monkeypatch):
    user = fake_user()

    monkeypatch.setattr(
        auth,
        "find_user_by_username",
        lambda username: user if username == "testuser" else None,
    )
    monkeypatch.setattr(
        auth,
        "find_user_by_id",
        lambda user_id: user if user_id == USER_ID else None,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "test-only-password",
            },
        )
        assert response.status_code == 200

        response = client.get("/api/auth/me")
        assert response.status_code == 200
        assert response.json()["username"] == "testuser"

        csrf_response = client.get("/api/auth/csrf")
        assert csrf_response.status_code == 200

        token = csrf_response.json()["csrf_token"]

        response = client.post(
            "/api/auth/logout",
            headers={"X-CSRF-Token": token},
        )
        assert response.status_code == 200

        response = client.get("/api/auth/me")
        assert response.status_code == 401


def test_wrong_password_rejected(monkeypatch):
    user = fake_user()

    monkeypatch.setattr(
        auth,
        "find_user_by_username",
        lambda username: user,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "incorrect-password",
            },
        )

    assert response.status_code == 401


def test_session_version_revokes_cookie(monkeypatch):
    user = fake_user()

    monkeypatch.setattr(
        auth,
        "find_user_by_username",
        lambda username: user,
    )
    monkeypatch.setattr(
        auth,
        "find_user_by_id",
        lambda user_id: user,
    )

    with TestClient(app) as client:
        login = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "test-only-password",
            },
        )
        assert login.status_code == 200

        assert client.get("/api/auth/me").status_code == 200

        # Simulate an administrator revoking all sessions.
        user["session_version"] += 1

        assert client.get("/api/auth/me").status_code == 401

def test_csrf_rejects_missing_token(monkeypatch):
    user = fake_user()

    monkeypatch.setattr(
        auth,
        "find_user_by_username",
        lambda username: user,
    )
    monkeypatch.setattr(
        auth,
        "find_user_by_id",
        lambda user_id: user,
    )

    with TestClient(app) as client:
        login = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "test-only-password",
            },
        )
        assert login.status_code == 200

        missing = client.post("/api/auth/logout")
        assert missing.status_code == 403

        invalid = client.post(
            "/api/auth/logout",
            headers={"X-CSRF-Token": "invalid-token"},
        )
        assert invalid.status_code == 403

        token = client.get(
            "/api/auth/csrf"
        ).json()["csrf_token"]

        valid = client.post(
            "/api/auth/logout",
            headers={"X-CSRF-Token": token},
        )
        assert valid.status_code == 200


def test_login_rate_limit(monkeypatch):
    from app.login_limiter import _failures

    user = fake_user()
    _failures.clear()

    monkeypatch.setattr(
        auth,
        "find_user_by_username",
        lambda username: user,
    )

    try:
        with TestClient(app) as client:
            for _ in range(5):
                response = client.post(
                    "/api/auth/login",
                    json={
                        "username": "testuser",
                        "password": "wrong-password",
                    },
                )
                assert response.status_code == 401

            blocked = client.post(
                "/api/auth/login",
                json={
                    "username": "testuser",
                    "password": "test-only-password",
                },
            )

            assert blocked.status_code == 429
            assert "Retry-After" in blocked.headers

    finally:
        _failures.clear()