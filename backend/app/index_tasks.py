"""Background document indexing tasks."""

from uuid import UUID

import psycopg
from fastapi import HTTPException

from app.celery_app import celery_app
from app.documents import database_url
from app.rag import index_document


def update_job(
    job_id: UUID,
    status: str,
    *,
    increment_attempts: bool = False,
    error: str | None = None,
):
    with psycopg.connect(database_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
                UPDATE document_index_jobs
                SET status = %s,
                    attempts = attempts + %s,
                    error = %s,
                    updated_at = now()
                WHERE id = %s
                """,
            (
                status,
                int(increment_attempts),
                error,
                job_id,
            ),
        )


@celery_app.task(
    bind=True,
    name="contextiq.index_document",
    max_retries=2,
)
def index_document_job(
    self,
    job_id: str,
    document_id: str,
    owner_id: str,
):
    """Run ownership-checked indexing outside FastAPI."""

    job_uuid = UUID(job_id)

    update_job(
        job_uuid,
        "running",
        increment_attempts=True,
    )

    try:
        # Reuse the existing indexing implementation.
        # It rechecks ownership before writing embeddings.
        result = index_document(
            UUID(document_id),
            UUID(owner_id),
        )

    except Exception as exc:
        retryable = (
            isinstance(exc, psycopg.OperationalError)
            or (
                isinstance(exc, HTTPException)
                and exc.status_code == 503
            )
        )

        if retryable and self.request.retries < 2:
            update_job(
                job_uuid,
                "queued",
                error="Temporary service failure; retrying",
            )

            raise self.retry(
                exc=exc,
                countdown=5 * (2 ** self.request.retries),
            )

        update_job(
            job_uuid,
            "failed",
            error="Indexing failed; check worker logs",
        )
        raise

    update_job(job_uuid, "succeeded")

    return result