"""Authenticated, read-only ContextIQ load testing."""

import os

from locust import HttpUser, between, task
from locust.exception import StopUser


class ContextIQUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        username = os.getenv("CONTEXTIQ_LOAD_USERNAME")
        password = os.getenv("CONTEXTIQ_LOAD_PASSWORD")

        if not username or not password:
            raise RuntimeError(
                "Set CONTEXTIQ_LOAD_USERNAME and "
                "CONTEXTIQ_LOAD_PASSWORD before testing."
            )

        with self.client.post(
            "/api/auth/login",
            json={
                "username": username,
                "password": password,
            },
            name="POST /api/auth/login",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(
                    f"Login failed: HTTP {response.status_code}"
                )
                raise StopUser()

            response.success()

    @task(3)
    def list_documents(self):
        self.client.get(
            "/api/documents",
            name="GET /api/documents",
        )

    @task(2)
    def indexing_status(self):
        self.client.get(
            "/api/rag/status",
            name="GET /api/rag/status",
        )

    @task(1)
    def health(self):
        self.client.get(
            "/api/health",
            name="GET /api/health",
        )