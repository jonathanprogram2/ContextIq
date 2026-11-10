"""Controlled recovery of abandoned indexing jobs."""

import argparse
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.documents import database_url


def recover_job(job_id: UUID, min_age_minutes: int, apply: bool) -> str:
    with psycopg.connect(
        database_url(), row_factory=dict_row
    ) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, status, attempts, updated_at
            FROM document_index_jobs
            WHERE id = %s
            FOR UPDATE
            """,
            (job_id,),
        )

        job = cur.fetchone()

        if job is None:
            return "Job not found."

        if job["status"] not in ("queued", "running"):
            return f"Job is already {job['status']}; no action needed."

        cur.execute(
            """
            SELECT updated_at <=
                now() - (%s * INTERVAL '1 minute')
                AS is_stale
            FROM document_index_jobs
            WHERE id = %s
            """,
            (min_age_minutes, job_id),
        )

        if not cur.fetchone()["is_stale"]:
            return "Job is not old enough for recovery."

        if not apply:
            return (
                f"DRY RUN: job {job_id} is {job['status']} "
                "and eligible for manual recovery."
            )

        cur.execute(
            """
            UPDATE document_index_jobs
            SET status = 'failed',
                error = 'Manually recovered after worker shutdown',
                updated_at = now()
            WHERE id = %s
              AND status IN ('queued', 'running')
            RETURNING id
            """,
            (job_id,),
        )

        if cur.fetchone() is None:
            return "Job state changed; no action performed."

        return f"Job {job_id} marked failed. Reindex through the UI."


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("job_id", type=UUID)
    parser.add_argument(
        "--minutes", type=int, default=30
    )
    parser.add_argument(
        "--apply", action="store_true"
    )
    parser.add_argument(
        "--confirm-workers-stopped",
        action="store_true",
    )
    args = parser.parse_args()

    if args.minutes < 1:
        parser.error("--minutes must be positive")

    if args.apply and not args.confirm_workers_stopped:
        parser.error(
            "--apply requires --confirm-workers-stopped"
        )

    print(
        recover_job(
            args.job_id,
            args.minutes,
            args.apply,
        )
    )


if __name__ == "__main__":
    main()