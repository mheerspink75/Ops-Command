"""Celery application backed by a Redis broker."""

from __future__ import annotations

from celery import Celery

from app.config import get_settings


def create_celery() -> Celery:
    settings = get_settings()
    app = Celery(
        "opscommand",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["app.worker.tasks"],
    )
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        broker_connection_retry_on_startup=True,
    )
    return app


celery_app = create_celery()
