import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import psycopg
from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.agentic import router as agent_router
from app.auth import require_auth
from app.auth import router as auth_router
from app.documents import router as documents_router
from app.jobs import router as jobs_router
from app.rag import router as rag_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

session_secret = os.getenv("CONTEXTIQ_SESSION_SECRET")

if not session_secret:
    raise RuntimeError(
        "CONTEXTIQ_SESSION_SECRET must be configured"
    )
app = FastAPI(title="ContextIQ API", version="0.1.0", lifespan=lifespan)
app.include_router(auth_router)

app.include_router(
    documents_router,
    dependencies=[Depends(require_auth)],
)

app.include_router(
    rag_router,
    dependencies=[Depends(require_auth)],
)

app.include_router(
    agent_router,
    dependencies=[Depends(require_auth)],
)

app.include_router(
    jobs_router,
    dependencies=[Depends(require_auth)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    session_cookie="contextiq_session",
    same_site="strict",
    https_only=os.getenv("CONTEXTIQ_COOKIE_SECURE", "0") == "1",
    max_age=3600,
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"

    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"

    return response

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "contextiq-api"}


def check_database():
    url = os.getenv(
        "DATABASE_URL",
        "postgresql://contextiq:localdev_only_change_me@localhost:5432/contextiq",
    )
    try:    
        with psycopg.connect(url, connect_timeout=2) as conn, conn.cursor() as cur:
            cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            return "ok" if cur.fetchone() else "pgvector extension missing"

    except psycopg.Error:
        return "unavailable"


def check_blob():
    url = os.getenv("AZURITE_BLOB_URL", "http://127.0.0.1:10000/devstoreaccount1")
    try:
        with httpx.Client(timeout=2) as client:
            response = client.get(url, params={"comp": "list"})
        # An authentication error is expected without a signed request;
        # it still proves the local blob service is reachable.
        return "ok" if response.status_code in (200, 400, 403) and "Azurite" in response.headers.get("server", "") else "unavailable"
    except httpx.HTTPError:
        return "unavailable"


@app.get("/api/ready")
def ready():
    checks = {"database": check_database(), "blob_emulator": check_blob()}
    return {"status": "ready" if all(v == "ok" for v in checks.values()) else "degraded", "checks": checks}
