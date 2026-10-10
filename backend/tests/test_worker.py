"""Tests for playbook worker execution: retries, permanent failures, idempotency.

These exercise the service-layer execution engine directly (the same code path
the Celery task invokes), with an injected webhook caller so retry behavior is
deterministic and fast.
"""

from __future__ import annotations

from app.db.models.playbook import Playbook
from app.services import playbook_service


def _make_playbook(db_session, org, steps, name="Worker Playbook"):
    p = Playbook(
        organization_id=org.id,
        name=name,
        enabled=True,
        steps=steps,
    )
    db_session.add(p)
    db_session.flush()
    return p


def _start(db_session, org, incident, playbook, key):
    run, created = playbook_service.start_run(
        db_session,
        incident_id=incident.id,
        org_id=org.id,
        playbook_id=playbook.id,
        idempotency_key=key,
    )
    assert created
    return run


class TestRetryBehavior:
    def test_transient_failure_retries_then_succeeds(self, db_session, org, incident):
        pb = _make_playbook(
            db_session,
            org,
            [{"type": "mock_webhook", "params": {"url": "https://example.com/hook"}}],
        )
        run = _start(db_session, org, incident, pb, "retry-succeed")

        calls = {"n": 0}

        def flaky(payload):
            calls["n"] += 1
            if calls["n"] <= 2:
                raise playbook_service.TransientError("transient failure")
            return {"status": 200}

        result = playbook_service.execute_run(
            db_session,
            run_id=run.id,
            webhook_caller=flaky,
            max_retries=3,
            base_delay=0.01,
        )
        assert result.status == "succeeded"
        assert calls["n"] == 3  # two transient failures, then success
        assert result.progress[-1]["status"] == "done"

    def test_transient_failure_exhausts_retries(self, db_session, org, incident):
        pb = _make_playbook(
            db_session,
            org,
            [{"type": "mock_webhook", "params": {"url": "https://example.com/hook"}}],
        )
        run = _start(db_session, org, incident, pb, "retry-exhaust")

        def always_fail(payload):
            raise playbook_service.TransientError("always fails")

        result = playbook_service.execute_run(
            db_session,
            run_id=run.id,
            webhook_caller=always_fail,
            max_retries=2,
            base_delay=0.01,
        )
        assert result.status == "failed"
        assert "failed after 2 retries" in (result.error_detail or "")

    def test_permanent_failure_stops_immediately(self, db_session, org, incident):
        # Unknown step type raises PermanentError.
        pb = _make_playbook(
            db_session,
            org,
            [{"type": "not_a_real_step", "params": {}}],
        )
        run = _start(db_session, org, incident, pb, "permanent")

        calls = {"n": 0}

        def caller(payload):
            calls["n"] += 1
            return {"status": 200}

        result = playbook_service.execute_run(
            db_session,
            run_id=run.id,
            webhook_caller=caller,
            max_retries=3,
            base_delay=0.01,
        )
        assert result.status == "failed"
        assert "Unknown step type" in (result.error_detail or "")
        # Permanent errors must not be retried.
        assert calls["n"] == 0


class TestExecutionIdempotency:
    def test_terminal_run_not_reexecuted(self, db_session, org, incident):
        pb = _make_playbook(
            db_session,
            org,
            [{"type": "timeline_message", "params": {"message": "once"}}],
        )
        run = _start(db_session, org, incident, pb, "idempotent")

        calls = {"n": 0}

        def counting_caller(payload):
            calls["n"] += 1
            return {"status": 200}

        first = playbook_service.execute_run(
            db_session,
            run_id=run.id,
            webhook_caller=counting_caller,
            max_retries=3,
            base_delay=0.01,
        )
        assert first.status == "succeeded"

        # A duplicate delivery must be a no-op (terminal guard).
        second = playbook_service.execute_run(
            db_session,
            run_id=run.id,
            webhook_caller=counting_caller,
            max_retries=3,
            base_delay=0.01,
        )
        assert second.status == "succeeded"
        # The timeline message step should have run exactly once.
        timeline = [e for e in incident.timeline if e.event_type == "playbook"]
        assert len(timeline) == 1


class TestStepExecution:
    def test_timeline_message_step(self, db_session, org, incident):
        pb = _make_playbook(
            db_session,
            org,
            [{"type": "timeline_message", "params": {"message": "Step ran"}}],
        )
        run = _start(db_session, org, incident, pb, "timeline-step")
        result = playbook_service.execute_run(
            db_session,
            run_id=run.id,
            webhook_caller=lambda p: {"status": 200},
            max_retries=3,
            base_delay=0.01,
        )
        assert result.status == "succeeded"
        assert any(e.message == "Step ran" for e in incident.timeline)

    def test_create_action_item_step(self, db_session, org, incident):
        pb = _make_playbook(
            db_session,
            org,
            [{"type": "create_action_item", "params": {"title": "From playbook"}}],
        )
        run = _start(db_session, org, incident, pb, "action-step")
        result = playbook_service.execute_run(
            db_session,
            run_id=run.id,
            webhook_caller=lambda p: {"status": 200},
            max_retries=3,
            base_delay=0.01,
        )
        assert result.status == "succeeded"
        assert any(i.title == "From playbook" for i in incident.action_items)

    def test_publisher_receives_progress_and_final(self, db_session, org, incident):
        pb = _make_playbook(
            db_session,
            org,
            [
                {"type": "timeline_message", "params": {"message": "a"}},
                {"type": "timeline_message", "params": {"message": "b"}},
            ],
        )
        run = _start(db_session, org, incident, pb, "publish")

        events = []
        result = playbook_service.execute_run(
            db_session,
            run_id=run.id,
            webhook_caller=lambda p: {"status": 200},
            publisher=lambda e: events.append(e),
            max_retries=3,
            base_delay=0.01,
        )
        assert result.status == "succeeded"
        statuses = [e["status"] for e in events]
        assert statuses.count("progress") == 2
        assert statuses[-1] == "succeeded"
