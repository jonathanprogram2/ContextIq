"""Local single-administrator authentication."""

import os
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from psycopg.rows import dict_row
from pwdlib import PasswordHash
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/auth", tags=["authentication"])
password_hash = PasswordHash.recommended()


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


def require_auth(request: Request) -> None:
    if request.session.get("user") != "local-admin":
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

def current_user_id(request: Request) -> UUID:
    """Resolve the authenticated session to a database user."""

    require_auth(request)

    username = request.session["user"]

    url = os.getenv(
        "DATABASE_URL",
        "postgresql://contextiq:localdev_only_change_me"
        "@127.0.0.1:5433/contextiq",
    )

    with psycopg.connect(
        url,
        row_factory=dict_row,
    ) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id
            FROM users
            WHERE username = %s
            """,
            (username,),
        )

        user = cur.fetchone()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User account no longer exists",
        )

    return user["id"]

@router.post("/login")
def login(payload: LoginRequest, request: Request):
    stored_hash = os.getenv("CONTEXTIQ_ADMIN_PASSWORD_HASH")

    if not stored_hash:
        raise HTTPException(
            status_code=503,
            detail="Administrator authentication not configured",
        )

    if not password_hash.verify(payload.password, stored_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    request.session.clear()
    request.session["user"] = "local-admin"

    return {"authenticated": True}


@router.get("/me", dependencies=[Depends(require_auth)])
def current_user():
    return {"authenticated": True, "role": "admin"}


@router.post("/logout", dependencies=[Depends(require_auth)])
def logout(request: Request):
    request.session.clear()
    return {"authenticated": False}