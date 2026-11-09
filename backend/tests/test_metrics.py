"""Observability endpoint regression tests."""

from fastapi.testclient import TestClient

from app import metrics
from app.main import app


def test_metrics_endpoint_exposes_prometheus_data(monkeypatch):
    # Keep this unit test independent of PostgreSQL.
    monkeypatch.setattr(
        metrics,
        "refresh_job_metrics",
        lambda: None,
    )

    with TestClient(app) as client:
        client.get("/api/health")
        response = client.get("/metrics")

    assert response.status_code == 200
    assert "contextiq_http_requests_total" in response.text
    assert "contextiq_http_request_duration_seconds" in response.text
    assert "text/plain" in response.headers["content-type"]


def test_api_security_headers():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"