"""Initialize persistent document indexing job storage."""

import psycopg

from app.documents import database_url


def setup_index_jobs():
    with psycopg.connect(database_url()) as conn, conn.cursor() as cur:
        cur.execute("""
                CREATE TABLE IF NOT EXISTS document_index_jobs (
                    id UUID PRIMARY KEY,
                    document_id UUID NOT NULL
                        REFERENCES documents(id) ON DELETE CASCADE,
                    owner_id UUID NOT NULL REFERENCES users(id),
                    status TEXT NOT NULL DEFAULT 'queued'
                        CHECK (
                            status IN (
                                'queued',
                                'running',
                                'succeeded',
                                'failed'
                            )
                        ),
                    attempts INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)

        cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                    one_active_index_job_per_document
                ON document_index_jobs (document_id)
                WHERE status IN ('queued', 'running')
            """)

        cur.execute("""
                CREATE INDEX IF NOT EXISTS
                    document_index_jobs_owner_created
                ON document_index_jobs (
                    owner_id, created_at DESC
                )
            """)

    print("Document indexing job schema ready.")


if __name__ == "__main__":
    setup_index_jobs()