"""Celery tasks for playbook execution.

The task is idempotent: `execute_run` checks terminal status before doing work,
so duplicate delivery is safe. Step-level retries with exponential backoff live
in the service layer.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

import httpx

from app.db.session import session_scope
from app.observability.metrics import record_worker_task
from app.realtime.hub import hub
from app.services import playbook_service
from app.worker.broker import celery_app

logger = logging.getLogger(__name__)


def default_webhook_caller(payload: dict[str, Any]) -> Any:
    """Call a (mock) webhook endpoint. Failures raise so the step can retry."""
    url = payload["url"]
    body = payload.get("payload", {})
    resp = httpx.post(url, json=body, timeout=10)
    resp.raise_for_status()
    return {"status": resp.status_code}


def _publisher(incident_id: str):
    def publish(event: dict[str, Any]) -> None:
        hub.publish(incident_id, event)

    return publish


@celery_app.task(bind=True, max_retries=2, default_retry_delay=1)
def execute_playbook_run(self, run_id: str) -> None:
    started = time.perf_counter()
    result = "success"
    try:
        with session_scope() as session:
            playbook_service.execute_run(
                session,
                run_id=uuid.UUID(run_id),
                webhook_caller=default_webhook_caller,
                publisher=_publisher(run_id),
            )
    except Exception:  # noqa: BLE001
        result = "failure"
        logger.exception("playbook run %s failed", run_id)
        raise
    finally:
        record_worker_task("execute_playbook_run", result, time.perf_counter() - started)


def dispatch_playbook_run(run_id: str) -> None:
    """Enqueue a playbook run for background execution."""
    execute_playbook_run.delay(run_id)


def run_playbook_run_sync(run_id: str) -> None:
    """Run a playbook run synchronously (used by tests and the dev fallback)."""
    execute_playbook_run.run(run_id)
