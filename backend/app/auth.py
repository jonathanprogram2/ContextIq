"""Local single-administrator authentication."""

import os

from fastapi import APIRouter, Depends, HTTPException, Request
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