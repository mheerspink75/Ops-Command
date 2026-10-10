# ADR-006: Deterministic mock webhook for self-contained playbooks

**Status:** Accepted

## Context

Playbooks include a `mock_webhook` step that calls an external endpoint. For
local development and tests to be **reproducible** and **free**, we must not
depend on a paid or flaky external API. Yet we still want to exercise the real
code path (HTTP call, retry on failure, progress publishing).

## Decision

- Ship a tiny **mock-webhook** service (Python stdlib `http.server`) that
  echoes back the payload it receives and returns a stable `200`.
- The `mock_webhook` playbook step targets this service in local development
  and tests.
- The webhook caller is **injected** into the playbook service
  (`webhook_caller`), so production can substitute a real HTTP client without
  changing the execution engine.

## Consequences

- Playbooks and tests are fully self-contained, deterministic, and free.
- The real code path (call → retry → progress) is exercised end to end.
- The seam (`webhook_caller`) makes it straightforward to plug in real
  integrations (PagerDuty, Opsgenie, Slack) later.

## Alternatives considered

- **Calling a real external API in tests** — rejected: non-deterministic,
  costs money, and couples tests to third-party availability.
- **A full HTTP mock library (e.g. respx) only** — good for unit tests, but a
  real local service also lets the Docker stack and e2e tests exercise the
  network path.
- **No webhook step at all** — rejected: it is a core, realistic playbook
  capability we want to demonstrate.
