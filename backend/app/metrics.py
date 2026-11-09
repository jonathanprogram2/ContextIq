"""Prometheus metrics for ContextIQ."""

import psycopg
from fastapi import APIRouter
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.responses import Response

from app.documents import database_url

router = APIRouter(tags=["observability"])

HTTP_REQUESTS = Counter(
    "contextiq_http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"],
)

HTTP_DURATION = Histogram(
    "contextiq_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
    buckets=(
        0.005, 0.01, 0.025, 0.05,
        0.1, 0.25, 0.5, 1, 2, 5, 10,
    ),
)

INDEX_JOBS = Gauge(
    "contextiq_index_jobs",
    "Persistent document indexing jobs by status",
    ["status"],
)

METRICS_DB_UP = Gauge(
    "contextiq_metrics_database_up",
    "Whether the job-metrics database query succeeded",
)


def refresh_job_metrics() -> None:
    statuses = ("queued", "running", "succeeded", "failed")

    try:
        with psycopg.connect(
            database_url(),
            connect_timeout=2,
        ) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT status, COUNT(*)
                FROM document_index_jobs
                GROUP BY status
                """
            )
            counts = dict(cur.fetchall())
    except psycopg.Error:
        METRICS_DB_UP.set(0)
        return

    METRICS_DB_UP.set(1)

    for status in statuses:
        INDEX_JOBS.labels(status=status).set(
            counts.get(status, 0)
        )


@router.get("/metrics", include_in_schema=False)
def metrics():
    refresh_job_metrics()

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )