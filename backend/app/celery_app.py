"""Local Celery application for document indexing."""

import os

from celery import Celery

celery_app = Celery(
    "contextiq",
    broker=os.getenv(
        "CELERY_BROKER_URL",
        "redis://127.0.0.1:6379/0",
    ),
    include=["app.index_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": 3600,
    },
)