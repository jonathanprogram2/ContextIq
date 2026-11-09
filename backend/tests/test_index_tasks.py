"""Deterministic Celery reliability tests."""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app import index_tasks


def test_index_job_succeeds(monkeypatch):
    events = []
    job_id, document_id, owner_id = (
        uuid4(), uuid4(), uuid4()
    )

    monkeypatch.setattr(
        index_tasks,
        "claim_job",
        lambda *args: True,
    )

    monkeypatch.setattr(
        index_tasks,
        "finish_job",
        lambda *args, **kwargs: events.append(
            (args, kwargs)
        ),
    )

    monkeypatch.setattr(
        index_tasks,
        "index_document",
        lambda doc, owner: {
            "document_id": str(doc),
            "chunks_indexed": 4,
        },
    )

    result = index_tasks.index_document_job.run(
        str(job_id),
        str(document_id),
        str(owner_id),
    )

    assert result["chunks_indexed"] == 4
    assert events[-1][0][1] == "succeeded"


def test_duplicate_delivery_is_ignored(monkeypatch):
    called = []

    monkeypatch.setattr(
        index_tasks,
        "claim_job",
        lambda *args: False,
    )

    monkeypatch.setattr(
        index_tasks,
        "index_document",
        lambda *args: called.append(True),
    )

    result = index_tasks.index_document_job.run(
        str(uuid4()),
        str(uuid4()),
        str(uuid4()),
    )

    assert result["status"] == "ignored"
    assert called == []


def test_permanent_failure_is_recorded(monkeypatch):
    statuses = []

    monkeypatch.setattr(
        index_tasks,
        "claim_job",
        lambda *args: True,
    )

    monkeypatch.setattr(
        index_tasks,
        "finish_job",
        lambda job_id, status, **kwargs: statuses.append(
            status
        ),
    )

    def fail(*args):
        raise ValueError("Synthetic processing error")

    monkeypatch.setattr(
        index_tasks,
        "index_document",
        fail,
    )

    with pytest.raises(ValueError):
        index_tasks.index_document_job.run(
            str(uuid4()),
            str(uuid4()),
            str(uuid4()),
        )

    assert statuses == ["failed"]


def test_permanent_http_failure_is_recorded(monkeypatch):
    statuses = []

    monkeypatch.setattr(
        index_tasks,
        "claim_job",
        lambda *args: True,
    )

    monkeypatch.setattr(
        index_tasks,
        "finish_job",
        lambda job_id, status, **kwargs: statuses.append(
            status
        ),
    )

    def fail(*args):
        raise HTTPException(404, "Document not found")

    monkeypatch.setattr(
        index_tasks,
        "index_document",
        fail,
    )

    with pytest.raises(HTTPException):
        index_tasks.index_document_job.run(
            str(uuid4()),
            str(uuid4()),
            str(uuid4()),
        )

    assert statuses == ["failed"]