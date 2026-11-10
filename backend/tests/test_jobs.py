"""Authentication tests for background job API."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_job_submission_requires_authentication():
    with TestClient(app) as client:
        response = client.post(
            f"/api/jobs/index/{uuid4()}"
        )

    assert response.status_code == 401


def test_job_status_requires_authentication():
    with TestClient(app) as client:
        response = client.get(
            f"/api/jobs/{uuid4()}"
        )

    assert response.status_code == 401