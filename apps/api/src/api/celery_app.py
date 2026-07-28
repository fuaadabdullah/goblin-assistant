"""Celery application bootstrap for compose workers."""

from __future__ import annotations

import os

from celery import Celery

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", BROKER_URL)

app = Celery("goblin_assistant", broker=BROKER_URL, backend=RESULT_BACKEND)

# Keep runtime defaults minimal and broker startup resilient.
app.conf.update(
    broker_connection_retry_on_startup=True,
    task_default_queue="default",
    task_track_started=True,
    timezone="UTC",
    enable_utc=True,
)

# Preserve common name some integrations expect.
celery = app
