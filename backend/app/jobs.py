"""Authenticated API for asynchronous indexing jobs."""

from typing import Annotated
from uuid import UUID, uuid4

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from psycopg.rows import dict_row

from app.auth import current_user_id
from app.celery_app import celery_app
from app.documents import database_url

router = APIRouter(prefix="/api/jobs", tags=["background-jobs"])


@router.post("/index/{document_id}", status_code=202)
def enqueue_indexing(
    document_id: UUID,
    owner_id: Annotated[UUID, Depends(current_user_id)],
):
    job_id = uuid4()
    created = False

    with psycopg.connect(
        database_url(), row_factory=dict_row
    ) as conn, conn.cursor() as cur:

        cur.execute(
            """
            SELECT id
            FROM documents
            WHERE id = %s AND owner_id = %s
            """,
            (document_id, owner_id),
        )

        if cur.fetchone() is None:
            raise HTTPException(404, "Document not found")

        cur.execute(
            """
            INSERT INTO document_index_jobs
                (id, document_id, owner_id, status)
            VALUES (%s, %s, %s, 'queued')
            ON CONFLICT (document_id)
                WHERE status IN ('queued', 'running')
            DO NOTHING
            RETURNING id
            """,
            (job_id, document_id, owner_id),
        )

        inserted = cur.fetchone()

        if inserted:
            created = True
        else:
            cur.execute(
                """
                SELECT id
                FROM document_index_jobs
                WHERE document_id = %s
                  AND owner_id = %s
                  AND status IN ('queued', 'running')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (document_id, owner_id),
            )

            existing = cur.fetchone()

            if existing is None:
                raise HTTPException(
                    409,
                    "Job state changed; retry the request",
                )

            job_id = existing["id"]

    # The database transaction above has now committed.
    if created:
        try:
            celery_app.send_task(
                "contextiq.index_document",
                args=[
                    str(job_id),
                    str(document_id),
                    str(owner_id),
                ],
                task_id=str(job_id),
            )

        except Exception as exc:
            with (
                psycopg.connect(database_url()) as conn,
                conn.cursor() as cur,
            ):
                cur.execute(
                        """
                        UPDATE document_index_jobs
                        SET status = 'failed',
                            error = 'Could not queue indexing',
                            updated_at = now()
                        WHERE id = %s
                        """,
                        (job_id,),
                    )

            raise HTTPException(
                503,
                "Background job broker unavailable",
            ) from exc

    return {
        "job_id": str(job_id),
        "status": "queued",
        "created": created,
    }


@router.get("/{job_id}")
def get_index_job(
    job_id: UUID,
    owner_id: Annotated[UUID, Depends(current_user_id)],
):
    with psycopg.connect(
        database_url(), row_factory=dict_row
    ) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id::text AS job_id,
                   document_id::text AS document_id,
                   status,
                   attempts,
                   error,
                   created_at,
                   updated_at
            FROM document_index_jobs
            WHERE id = %s AND owner_id = %s
            """,
            (job_id, owner_id),
        )

        job = cur.fetchone()

    if job is None:
        raise HTTPException(404, "Job not found")

    job["created_at"] = job["created_at"].isoformat()
    job["updated_at"] = job["updated_at"].isoformat()

    return job