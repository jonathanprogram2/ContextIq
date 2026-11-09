"""Opt-in cross-user integration tests against local PostgreSQL."""

import os
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from pwdlib import PasswordHash

from app import retrieval
from app.auth import database_url
from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("CONTEXTIQ_RUN_INTEGRATION") != "1",
    reason="Requires local PostgreSQL integration environment",
)


@pytest.fixture
def isolated_users(monkeypatch):
    a_id, b_id = uuid4(), uuid4()
    a_doc, b_doc = uuid4(), uuid4()
    suffix = uuid4().hex[:12]
    username_a = f"isolated_a_{suffix}"
    username_b = f"isolated_b_{suffix}"
    password = "integration-test-password-only"
    hashed = PasswordHash.recommended().hash(password)

    vector = "[" + ",".join(["1"] + ["0"] * 767) + "]"

    with psycopg.connect(database_url()) as conn, conn.cursor() as cur:
        for user_id, username in (
            (a_id, username_a),
            (b_id, username_b),
        ):
            cur.execute(
                """
                    INSERT INTO users
                        (id, username, password_hash, role)
                    VALUES (%s, %s, %s, 'user')
                    """,
                (user_id, username, hashed),
            )

        for document_id, owner, label in (
            (a_doc, a_id, "alpha"),
            (b_doc, b_id, "beta"),
        ):
            cur.execute(
                """
                    INSERT INTO documents
                        (id, filename, blob_name, sha256,
                         size_bytes, page_count,
                         extracted_characters, status, owner_id)
                    VALUES
                        (%s, %s, %s, %s, %s, 1, 80,
                         'processed', %s)
                    """,
                (
                    document_id,
                    f"{label}.pdf",
                    f"{document_id}.pdf",
                    "test-only",
                    100,
                    owner,
                ),
            )

            cur.execute(
                """
                    INSERT INTO document_pages
                        (document_id, page_number, text_content)
                    VALUES (%s, 1, %s)
                    """,
                (document_id, f"{label} private information"),
            )

            cur.execute(
                """
                    INSERT INTO document_chunks
                        (document_id, page_number, chunk_number,
                         text_content, embedding, embedding_model)
                    VALUES (%s, 1, 1, %s, %s::vector, %s)
                    """,
                (
                    document_id,
                    f"{label} private information",
                    vector,
                    "nomic-embed-text",
                ),
            )

    monkeypatch.setattr(
        retrieval,
        "embed_texts",
        lambda texts: [[1.0] + [0.0] * 767],
    )

    yield {
        "a_id": a_id,
        "b_id": b_id,
        "a_doc": a_doc,
        "b_doc": b_doc,
        "username_a": username_a,
        "username_b": username_b,
        "password": password,
    }

    # Clean up only the test records created by this fixture.
    with psycopg.connect(database_url()) as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM documents WHERE id IN (%s, %s)",
            (a_doc, b_doc),
        )
        cur.execute(
            "DELETE FROM users WHERE id IN (%s, %s)",
            (a_id, b_id),
        )


def login(client, username, password):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200


def test_cross_user_document_and_retrieval_isolation(
    isolated_users,
):
    data = isolated_users

    with TestClient(app) as client_a, TestClient(app) as client_b:
        login(client_a, data["username_a"], data["password"])
        login(client_b, data["username_b"], data["password"])

        a_list = client_a.get("/api/documents")
        b_list = client_b.get("/api/documents")

        assert a_list.status_code == 200
        assert b_list.status_code == 200

        a_ids = {item["id"] for item in a_list.json()}
        b_ids = {item["id"] for item in b_list.json()}

        assert str(data["a_doc"]) in a_ids
        assert str(data["b_doc"]) not in a_ids
        assert str(data["b_doc"]) in b_ids
        assert str(data["a_doc"]) not in b_ids

        # Another user's page text is inaccessible.
        assert client_b.get(
            f"/api/documents/{data['a_doc']}/pages/1"
        ).status_code == 404

        # Another user's PDF cannot be downloaded.
        assert client_b.get(
            f"/api/documents/{data['a_doc']}/download"
        ).status_code == 404

        # Another user's document cannot be indexed.
        assert client_b.post(
            f"/api/rag/index/{data['a_doc']}"
        ).status_code == 404

        # Another user's document cannot be deleted.
        assert client_b.delete(
            f"/api/documents/{data['a_doc']}"
        ).status_code == 404

        # Index status lists only owned documents.
        a_status = client_a.get("/api/rag/status")
        b_status = client_b.get("/api/rag/status")

        assert a_status.status_code == 200
        assert b_status.status_code == 200

        a_indexed = {
            item["document_id"] for item in a_status.json()
        }
        b_indexed = {
            item["document_id"] for item in b_status.json()
        }

        assert str(data["b_doc"]) not in a_indexed
        assert str(data["a_doc"]) not in b_indexed

        # Exercise real PostgreSQL vector + keyword retrieval.
        a_result = retrieval.retrieve(
            "private information",
            top_k=4,
            mode="hybrid",
            owner_id=data["a_id"],
        )
        b_result = retrieval.retrieve(
            "private information",
            top_k=4,
            mode="hybrid",
            owner_id=data["b_id"],
        )

        a_source_ids = {
            item["document_id"] for item in a_result["sources"]
        }
        b_source_ids = {
            item["document_id"] for item in b_result["sources"]
        }

        assert str(data["a_doc"]) in a_source_ids
        assert str(data["b_doc"]) not in a_source_ids
        assert str(data["b_doc"]) in b_source_ids
        assert str(data["a_doc"]) not in b_source_ids