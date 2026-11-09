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


def claim_job(job_id: UUID, document_id: UUID, owner_id: UUID) -> bool:
    """Atomically claim one queued job for execution."""

    with psycopg.connect(database_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE document_index_jobs
            SET status = 'running',
                attempts = attempts + 1,
                error = NULL,
                updated_at = now()
            WHERE id = %s
              AND document_id = %s
              AND owner_id = %s
              AND status = 'queued'
              AND EXISTS (
                  SELECT 1
                  FROM documents
                  WHERE id = %s
                    AND owner_id = %s
              )
            RETURNING id
            """,
            (
                job_id,
                document_id,
                owner_id,
                document_id,
                owner_id,
            ),
        )

        return cur.fetchone() is not None
    

def finish_job(
    job_id: UUID,
    status: str,
    *,
    error: str | None = None,
) -> None:
    """Record a result only for a currently running job."""

    with psycopg.connect(database_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE document_index_jobs
            SET status = %s,
                error = %s,
                updated_at = now()
            WHERE id = %s
              AND status = 'running'
            """,
            (status, error, job_id),
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
    """Execute only jobs atomically claimed from PostgreSQL."""

    job_uuid = UUID(job_id)
    document_uuid = UUID(document_id)
    owner_uuid = UUID(owner_id)

    if not claim_job(job_uuid, document_uuid, owner_uuid):
        return {
            "status": "ignored",
            "reason": "Job is not queued or no longer authorized",
        }

    try:
        result = index_document(document_uuid, owner_uuid)

    except Exception as exc:
        retryable = (
            isinstance(exc, psycopg.OperationalError)
            or (
                isinstance(exc, HTTPException)
                and exc.status_code == 503
            )
        )

        if retryable and self.request.retries < 2:
            finish_job(
                job_uuid,
                "queued",
                error="Temporary failure; retry scheduled",
            )

            raise self.retry(
                exc=exc,
                countdown=5 * (2 ** self.request.retries),
            )

        finish_job(
            job_uuid,
            "failed",
            error="Indexing failed; inspect worker logs",
        )
        raise

    finish_job(job_uuid, "succeeded")
    return result