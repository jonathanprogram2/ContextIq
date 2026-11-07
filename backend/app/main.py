import os
from contextlib import asynccontextmanager

import httpx
import psycopg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agentic import router as agent_router
from app.documents import router as documents_router
from app.rag import router as rag_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="ContextIQ API", version="0.1.0", lifespan=lifespan)
app.include_router(documents_router)
app.include_router(rag_router)
app.include_router(agent_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


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
