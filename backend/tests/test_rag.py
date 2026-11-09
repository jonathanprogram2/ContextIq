"""CPU-only deterministic RAG tests; no Ollama or database required."""
from fastapi.testclient import TestClient

from app.auth import require_auth
from app.main import app
from app.rag import chunks_for_page, vector_literal

client = TestClient(app)


def test_chunking_preserves_source_text():
    chunks = chunks_for_page("hello world " * 130)
    assert len(chunks) > 1
    assert chunks[0].startswith("hello world")
    assert all(len(chunk) <= 900 for chunk in chunks)


def test_empty_pages_are_skipped():
    assert chunks_for_page(" \n ") == []


def test_vector_literal():
    assert vector_literal([0.1, -0.25]) == "[0.1,-0.25]"


def test_question_validation_before_inference():
    app.dependency_overrides[require_auth] = lambda: None

    try:
        response = client.post(
            "/api/rag/ask",
            json={"question": "a"},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.pop(require_auth, None)