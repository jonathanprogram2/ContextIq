"""Read-only diagnostic report for potentially stuck indexing jobs."""

import argparse

import psycopg
from psycopg.rows import dict_row

from app.documents import database_url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--minutes",
        type=int,
        default=30,
        help="Minimum age of a queued or running job",
    )
    args = parser.parse_args()

    if args.minutes < 1:
        parser.error("--minutes must be positive")

    with psycopg.connect(
        database_url(),
        row_factory=dict_row,
    ) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT j.id,
                   j.document_id,
                   j.status,
                   j.attempts,
                   j.updated_at,
                   d.filename
            FROM document_index_jobs j
            JOIN documents d ON d.id = j.document_id
            WHERE j.status IN ('queued', 'running')
              AND j.updated_at <
                  now() - (%s * INTERVAL '1 minute')
            ORDER BY j.updated_at
            """,
            (args.minutes,),
        )

        jobs = cur.fetchall()

    if not jobs:
        print("No potentially stuck indexing jobs found.")
        return

    print(f"Found {len(jobs)} potentially stuck jobs:")

    for job in jobs:
        print(
            f"Job: {job['id']} | "
            f"Status: {job['status']} | "
            f"Attempts: {job['attempts']} | "
            f"File: {job['filename']} | "
            f"Last update: {job['updated_at']}"
        )


if __name__ == "__main__":
    main()