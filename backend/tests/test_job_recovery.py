"""Tests for controlled indexing-job recovery."""

from uuid import uuid4

from app.scripts import recover_index_job


def test_missing_job_does_not_change_database(monkeypatch):
    class FakeCursor:
        def execute(self, query, params):
            pass

        def fetchone(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        recover_index_job.psycopg,
        "connect",
        lambda *args, **kwargs: FakeConnection(),
    )

    result = recover_index_job.recover_job(
        uuid4(),
        min_age_minutes=30,
        apply=False,
    )

    assert result == "Job not found."