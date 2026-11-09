"""Security regression tests for owner-scoped AI retrieval."""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app import retrieval
from app.auth import current_user_id, require_auth
from app.main import app

USER_A = UUID("11111111-1111-4111-8111-111111111111")
USER_B = UUID("22222222-2222-4222-8222-222222222222")


class FakeCursor:
    def __init__(self):
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params):
        self.queries.append((query, params))

    def fetchall(self):
        return []


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.fake_cursor


@pytest.mark.parametrize("owner_id", [USER_A, USER_B])
@pytest.mark.parametrize("mode", ["vector", "hybrid"])
def test_retrieval_queries_filter_by_owner(
    monkeypatch,
    owner_id,
    mode,
):
    cursor = FakeCursor()

    monkeypatch.setattr(
        retrieval,
        "embed_texts",
        lambda texts: [[0.1] * 768],
    )

    monkeypatch.setattr(
        retrieval.psycopg,
        "connect",
        lambda *args, **kwargs: FakeConnection(cursor),
    )

    result = retrieval.retrieve(
        "What does my handbook say?",
        top_k=4,
        mode=mode,
        owner_id=owner_id,
    )

    expected_queries = 2 if mode == "hybrid" else 1

    assert len(cursor.queries) == expected_queries
    assert result["sources"] == []

    for query, params in cursor.queries:
        assert "d.owner_id = %s" in query
        assert owner_id in params
        assert USER_B not in params if owner_id == USER_A else USER_A not in params


def test_retrieval_rejects_missing_owner():
    with pytest.raises(TypeError):
        retrieval.retrieve(
            "What does my handbook say?",
            top_k=4,
            mode="hybrid",
        )


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/rag/ask",
        "/api/agent/ask",
    ],
)
def test_ai_endpoints_require_login(endpoint):
    with TestClient(app) as client:
        response = client.post(
            endpoint,
            json={"question": "What is in my documents?"},
        )

    assert response.status_code == 401


def test_agent_passes_authenticated_owner_to_workflow(monkeypatch):
    from app import agentic

    captured = {}

    def fake_invoke(state, config=None):
        captured.update(state)

        return {
            "answer": "No supporting evidence.",
            "abstained": True,
            "sources": [],
            "attempts": 1,
            "latency_ms": 0.0,
        }

    monkeypatch.setattr(
        agentic.workflow,
        "invoke",
        fake_invoke,
    )

    app.dependency_overrides[require_auth] = lambda: None
    app.dependency_overrides[current_user_id] = lambda: USER_A

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/agent/ask",
                json={
                    "question": "What is in my documents?",
                    "mode": "hybrid",
                },
            )

        assert response.status_code == 200
        assert captured["owner_id"] == USER_A

    finally:
        app.dependency_overrides.pop(current_user_id, None)
        app.dependency_overrides.pop(require_auth, None)