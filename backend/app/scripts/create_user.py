"""Create a local ContextIQ user without public registration."""

import argparse
import getpass
import re
from pathlib import Path
from uuid import uuid4

import psycopg
from dotenv import load_dotenv
from pwdlib import PasswordHash

load_dotenv(Path(__file__).resolve().parents[3] / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.auth import database_url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    args = parser.parse_args()

    username = args.username.strip().lower()

    if not re.fullmatch(r"[a-z0-9_-]{3,40}", username):
        parser.error(
            "Username must be 3–40 characters: "
            "lowercase letters, numbers, _ or -"
        )

    password = getpass.getpass("New user password: ")
    confirmation = getpass.getpass("Confirm password: ")

    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    if len(password) < 12:
        raise SystemExit("Use at least 12 characters.")

    hashed = PasswordHash.recommended().hash(password)

    try:
        with psycopg.connect(database_url()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                    INSERT INTO users
                        (id, username, password_hash, role)
                    VALUES (%s, %s, %s, 'user')
                    """,
                (uuid4(), username, hashed),
            )
    except psycopg.errors.UniqueViolation:
        raise SystemExit("Username already exists.") from None

    print(f"Created user: {username}")


if __name__ == "__main__":
    main()