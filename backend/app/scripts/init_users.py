"""Initialize users and migrate existing documents to an owner."""

import os
from pathlib import Path
from uuid import uuid4

import psycopg
from dotenv import load_dotenv
from psycopg import sql

from app.documents import database_url

load_dotenv(
    Path(__file__).resolve().parents[3] / ".env"
)
load_dotenv(
    Path(__file__).resolve().parents[2] / ".env"
)

def setup_users():
    admin_hash = os.getenv(
        "CONTEXTIQ_ADMIN_PASSWORD_HASH"
    )

    if not admin_hash:
        raise RuntimeError(
            "Administrator password hash is missing"
        )

    with (
        psycopg.connect(database_url()) as conn,
        conn.cursor() as cur,
    ):
        # Serialize concurrent migrations.
        cur.execute(
            "SELECT pg_advisory_xact_lock(%s)",
            (20261108,),
        )

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
                    CHECK (role IN ('admin', 'user')),
                session_version INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)

        # Keep the existing administrator identity stable.
        cur.execute("""
            INSERT INTO users (
                id, username, password_hash, role
            )
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
        """, (
            uuid4(),
            "local-admin",
            admin_hash,
            "admin",
        ))

        cur.execute("""
            SELECT id FROM users
            WHERE username = 'local-admin'
        """)
        admin_id = cur.fetchone()[0]

        # Add the ownership field without dropping data.
        cur.execute("""
            ALTER TABLE documents
            ADD COLUMN IF NOT EXISTS owner_id UUID
        """)

        # Existing documents belong to the original admin.
        cur.execute("""
            UPDATE documents
            SET owner_id = %s
            WHERE owner_id IS NULL
        """, (admin_id,))

        # All future documents must have an owner.
        cur.execute("""
            ALTER TABLE documents
            ALTER COLUMN owner_id SET NOT NULL
        """)

        # Temporary compatibility with the single-admin upload API.
        cur.execute(
            sql.SQL(
                "ALTER TABLE documents "
                "ALTER COLUMN owner_id SET DEFAULT {}"
            ).format(sql.Literal(admin_id))
        )

        # Create the foreign key if not already present.
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'documents_owner_id_fkey'
                      AND conrelid = 'documents'::regclass
                ) THEN
                    ALTER TABLE documents
                    ADD CONSTRAINT documents_owner_id_fkey
                    FOREIGN KEY (owner_id)
                    REFERENCES users(id);
                END IF;
            END
            $$;
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS
                documents_owner_created_idx
            ON documents (owner_id, created_at DESC)
        """)

    print("User ownership schema ready.")


if __name__ == "__main__":
    setup_users()