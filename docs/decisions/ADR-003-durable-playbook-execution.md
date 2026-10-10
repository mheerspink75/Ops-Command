# ADR-003: Durable playbook execution with Celery + idempotency

**Status:** Accepted

## Context

Playbooks are multi-step runbooks that may call external endpoints and take
time. They must:

- **Survive** API restarts (not run in the request).
- Be **safe to retry** (a duplicate dispatch must not double-execute).
- **Retry** transient failures (e.g. a flaky webhook) and stop on permanent
  ones.
- Stream **progress** to the UI in real time.
- Never leak **secrets** into failure details.

## Decision

- Playbook runs are **dispatched** to a Celery worker (Redis broker) via
  `execute_playbook_run.delay(run_id)`.
- A `PlaybookRun` row is created **before** dispatch (status `pending`), so
  the run is durable and observable even if the worker is slow.
- **Idempotency:** runs are keyed by `idempotency_key`; a duplicate dispatch
  returns the existing run. The task also re-checks terminal status before
  doing work, so duplicate delivery is a no-op.
- **Retries:** transient step failures retry with exponential backoff up to a
  maximum; permanent failures stop the run and record a sanitized error.
- **Progress:** each step's result is persisted and published via the
  `RealtimeHub` (see ADR-002).

## Consequences

- Background execution is decoupled from the API; the API stays responsive.
- Idempotency + terminal-status guard make the system safe under at-least-once
  delivery and manual re-dispatch.
- Adds a runtime dependency (a running worker) for playbook execution —
  documented in the README and enforced by the e2e preconditions.

## Alternatives considered

- **Synchronous execution in the request** — rejected: blocks the API and is
  not durable.
- **A database-backed job queue** — viable and removes the Celery dependency,
  but Celery + Redis is already present and provides retries/monitoring out of
  the box.
- **A step-level state machine persisted per step** — considered for very long
  playbooks; the current per-run progress list is sufficient for this scope.
