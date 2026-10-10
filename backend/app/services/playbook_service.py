"""Playbook execution service.

Playbooks run as ordered steps. Execution is:
- Idempotent: a run is keyed by an idempotency key; duplicate delivery returns
  the existing run instead of re-executing.
- Retriable: transient step failures retry with exponential backoff up to a
  maximum; permanent failures stop the run.
- Observable: step-level progress is persisted and published in real time.
- Safe: failure details never include secrets.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.db.models.incident import Incident
from app.db.models.playbook import Playbook, PlaybookRun
from app.services import incident_service

MAX_WAIT_SECONDS = 30  # dev-safe cap for the 'wait' step


class TransientError(Exception):
    """A retryable failure."""


class PermanentError(Exception):
    """A non-retryable failure."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


def start_run(
    session: Session,
    *,
    incident_id: uuid.UUID,
    org_id: uuid.UUID,
    playbook_id: uuid.UUID,
    idempotency_key: str,
) -> tuple[PlaybookRun, bool]:
    """Create a run (or return the existing one for a duplicate key).

    Returns (run, created). `created` is False when an existing run was reused,
    which lets the caller skip re-dispatching the worker task.
    """
    existing = (
        session.query(PlaybookRun)
        .filter(
            PlaybookRun.incident_id == incident_id,
            PlaybookRun.idempotency_key == idempotency_key,
        )
        .first()
    )
    if existing is not None:
        return existing, False

    playbook = session.get(Playbook, playbook_id)
    if playbook is None or playbook.organization_id != org_id:
        raise NotFoundError("Playbook not found")
    if not playbook.enabled:
        raise ForbiddenError("Playbook is disabled")

    # Ensure the incident belongs to the org.
    incident = (
        session.query(Incident)
        .filter(Incident.id == incident_id, Incident.organization_id == org_id)
        .first()
    )
    if incident is None:
        raise NotFoundError("Incident not found")

    run = PlaybookRun(
        incident_id=incident_id,
        playbook_id=playbook_id,
        status="pending",
        idempotency_key=idempotency_key,
        progress=[],
        created_at=_utcnow(),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run, True


def _execute_step(
    session: Session,
    incident: Incident,
    step: dict[str, Any],
    *,
    webhook_caller: Callable[[dict[str, Any]], Any],
) -> dict[str, Any]:
    step_type = step.get("type")
    params = step.get("params", {}) or {}

    if step_type == "timeline_message":
        message = params.get("message", "Playbook step executed")
        incident_service.add_timeline_event(
            session,
            incident_id=incident.id,
            org_id=incident.organization_id,
            actor=None,
            event_type="playbook",
            message=message,
            metadata={"playbook_step": step_type},
        )
        return {"message": message}

    if step_type == "create_action_item":
        item = incident_service.create_action_item(
            session,
            incident_id=incident.id,
            org_id=incident.organization_id,
            actor=None,  # type: ignore[arg-type]
            title=params.get("title", "Playbook action item"),
            description=params.get("description"),
            assignee_id=params.get("assignee_id"),
            status=params.get("status", "open"),
            due_at=None,
        )
        return {"action_item_id": str(item.id)}

    if step_type == "change_status":
        target = params.get("status")
        if target is None:
            raise PermanentError("change_status step requires 'status'")
        if incident.status == target:
            return {"skipped": True, "reason": "already in target status"}
        if target not in incident_service.VALID_TRANSITIONS.get(incident.status, set()):
            # Lenient: skip invalid transitions rather than failing the run.
            return {"skipped": True, "reason": f"invalid transition to {target}"}
        # Reload to get a fresh object for the transition.
        fresh = session.get(Incident, incident.id)
        if fresh is None:
            raise PermanentError("Incident no longer exists")
        incident_service.transition_status(
            session,
            incident_id=incident.id,
            org_id=incident.organization_id,
            actor=None,  # type: ignore[arg-type]
            new_status=target,
            expected_version=fresh.version,
        )
        return {"status": target}

    if step_type == "wait":
        delay = float(params.get("seconds", 0))
        delay = max(0.0, min(delay, MAX_WAIT_SECONDS))
        time.sleep(delay)
        return {"waited_seconds": delay}

    if step_type == "mock_webhook":
        url = params.get("url")
        if not url:
            raise PermanentError("mock_webhook step requires 'url'")
        try:
            result = webhook_caller({"url": url, "payload": params.get("payload", {})})
        except TransientError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalize to transient for retry
            raise TransientError(f"webhook call failed: {exc}") from exc
        return {"webhook": "ok", "response": result}

    if step_type == "snapshot":
        from app.services import report_service

        content = report_service.generate_report(
            session, incident_id=incident.id, org_id=incident.organization_id
        )
        return {"snapshot_chars": len(content)}

    raise PermanentError(f"Unknown step type: {step_type}")


def execute_run(
    session: Session,
    *,
    run_id: uuid.UUID,
    webhook_caller: Callable[[dict[str, Any]], Any],
    publisher: Callable[[dict[str, Any]], None] | None = None,
    max_retries: int = 3,
    base_delay: float = 0.1,
) -> PlaybookRun:
    """Execute a playbook run step-by-step with retries and progress tracking."""
    run = session.get(PlaybookRun, run_id)
    if run is None:
        raise NotFoundError("Playbook run not found")

    # Idempotency guard: if already terminal, do nothing (safe duplicate delivery).
    if run.status in {"succeeded", "failed"}:
        return run

    playbook = session.get(Playbook, run.playbook_id)
    incident = session.get(Incident, run.incident_id)
    if playbook is None or incident is None:
        run.status = "failed"
        run.error_detail = "Playbook or incident no longer exists"
        run.completed_at = _utcnow()
        session.commit()
        return run

    run.status = "running"
    run.started_at = _utcnow()
    session.commit()

    progress: list[dict[str, Any]] = []
    steps = playbook.steps or []

    for index, step in enumerate(steps):
        attempt = 0
        while True:
            try:
                # Reload incident to reflect prior step mutations.
                fresh = session.get(Incident, incident.id)
                if fresh is None:
                    raise PermanentError("Incident no longer exists")
                result = _execute_step(session, fresh, step, webhook_caller=webhook_caller)
                progress.append(
                    {"index": index, "type": step.get("type"), "status": "done", "result": result}
                )
                break
            except TransientError:
                attempt += 1
                if attempt > max_retries:
                    run.status = "failed"
                    run.error_detail = (
                        f"Step {index} ({step.get('type')}) failed after {max_retries} retries"
                    )
                    run.progress = progress
                    run.completed_at = _utcnow()
                    session.commit()
                    _publish(publisher, run, "failed")
                    return run
                time.sleep(base_delay * (2 ** (attempt - 1)))
            except PermanentError as exc:
                run.status = "failed"
                run.error_detail = f"Step {index} ({step.get('type')}) failed: {exc}"
                run.progress = progress
                run.completed_at = _utcnow()
                session.commit()
                _publish(publisher, run, "failed")
                return run

        run.progress = progress
        session.commit()
        _publish(publisher, run, "progress")

    run.status = "succeeded"
    run.completed_at = _utcnow()
    session.commit()
    _publish(publisher, run, "succeeded")
    return run


def _publish(
    publisher: Callable[[dict[str, Any]], None] | None,
    run: PlaybookRun,
    event: str,
) -> None:
    if publisher is None:
        return
    try:
        publisher(
            {
                "type": "playbook_progress",
                "incident_id": str(run.incident_id),
                "run_id": str(run.id),
                "status": event,
                "progress": run.progress,
            }
        )
    except Exception:  # noqa: BLE001 - publishing must not break execution
        pass
