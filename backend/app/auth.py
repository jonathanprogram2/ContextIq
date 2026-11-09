"""Database-backed authentication for local ContextIQ users."""

import os
from typing import Annotated
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from psycopg.rows import dict_row
from pwdlib import PasswordHash
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/auth", tags=["authentication"])
password_hash = PasswordHash.recommended()


def database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://contextiq:localdev_only_change_me"
        "@127.0.0.1:5433/contextiq",
    )


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


def find_user_by_username(username: str) -> dict | None:
    with psycopg.connect(
        database_url(), row_factory=dict_row
    ) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, username, password_hash,
                   role, session_version
            FROM users
            WHERE username = %s
            """,
            (username,),
        )
        return cur.fetchone()


def find_user_by_id(user_id: UUID) -> dict | None:
    with psycopg.connect(
        database_url(), row_factory=dict_row
    ) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, username, role, session_version
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        return cur.fetchone()


def require_auth(request: Request) -> dict:
    """Validate the signed session against the current user record."""
    raw_id = request.session.get("uid")
    version = request.session.get("version")

    if not isinstance(raw_id, str) or type(version) is not int:
        raise HTTPException(401, "Authentication required")

    try:
        user_id = UUID(raw_id)
    except ValueError as exc:
        raise HTTPException(401, "Invalid session") from exc

    user = find_user_by_id(user_id)

    if user is None or user["session_version"] != version:
        raise HTTPException(401, "Session expired or revoked")

    return user


def current_user_id(request: Request) -> UUID:
    """Return the ID of the authenticated database user."""
    return require_auth(request)["id"]


@router.post("/login")
def login(payload: LoginRequest, request: Request):
    username = payload.username.strip().lower()
    user = find_user_by_username(username)

    if user is None or not password_hash.verify(
        payload.password, user["password_hash"]
    ):
        raise HTTPException(401, "Invalid credentials")

    request.session.clear()
    request.session["uid"] = str(user["id"])
    request.session["version"] = user["session_version"]

    return {
        "authenticated": True,
        "username": user["username"],
        "role": user["role"],
    }


@router.get("/me")
def current_user(
    user: Annotated[dict, Depends(require_auth)],
):
    return {
        "authenticated": True,
        "id": str(user["id"]),
        "username": user["username"],
        "role": user["role"],
    }


@router.post("/logout")
def logout(
    request: Request,
    _user: Annotated[dict, Depends(require_auth)],
):
    request.session.clear()
    return {"authenticated": False}