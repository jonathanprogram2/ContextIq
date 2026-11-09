"""Deterministic background indexing task tests."""

from uuid import uuid4

import pytest

from app import index_tasks


def test_index_job_succeeds(monkeypatch):
    events = []
    job_id = uuid4()
    document_id = uuid4()
    owner_id = uuid4()

    monkeypatch.setattr(
        index_tasks,
        "update_job",
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
    assert events[0][0][1] == "running"
    assert events[-1][0][1] == "succeeded"


def test_index_job_records_permanent_failure(monkeypatch):
    events = []

    def fail_indexing(document_id, owner_id):
        raise ValueError("Synthetic indexing error")

    monkeypatch.setattr(
        index_tasks,
        "update_job",
        lambda *args, **kwargs: events.append(
            (args, kwargs)
        ),
    )

    monkeypatch.setattr(
        index_tasks,
        "index_document",
        fail_indexing,
    )

    with pytest.raises(ValueError):
        index_tasks.index_document_job.run(
            str(uuid4()),
            str(uuid4()),
            str(uuid4()),
        )

    assert events[-1][0][1] == "failed"