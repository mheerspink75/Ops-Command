# ADR-002: Real-time delivery via in-process hub + Redis pub/sub bridge

**Status:** Accepted

## Context

The command view must update the moment anything changes — including changes
made by a **background worker** in a separate process (e.g. playbook progress).
A single-process in-memory pub/sub is not enough because the worker and the
API are different OS processes. We also want real-time to be an
optimization, not a correctness dependency: REST remains the source of truth.

## Decision

- A `RealtimeHub` delivers events to **in-process** subscribers
  (`subscribe`/`publish`) for the common case where the mutation and the
  WebSocket live in the same API process.
- `publish` **also** does a Redis `PUBLISH` to `opscommand:incident:<id>`.
- A daemon thread in the API process runs `PSUBSCRIBE opscommand:incident:*`
  and forwards matching messages to the in-process subscribers. This bridges
  events from the worker (or another API replica) to the browser.
- Delivery is **at-most-once** and best-effort; a failing subscriber is caught
  and logged so it cannot break others; Redis is optional (in-process delivery
  still works if Redis is down).

## Consequences

- Cross-process real-time works with minimal infrastructure (Redis is already
  present for the Celery broker and throttling).
- Simple to reason about and to scale: each API replica runs its own bridge;
  Redis fans events out.
- Not a durable queue — clients must treat REST as authoritative and use
  WebSockets for liveness. This is an acceptable trade-off for this scope.

## Alternatives considered

- **Server-Sent Events (SSE)** — viable, but WebSockets fit the bidirectional
  heartbeat model and are already well-supported by FastAPI.
- **A dedicated message broker (e.g. NATS, Kafka)** — more robust for
  at-least-once delivery and replay, but heavier than this project needs;
  noted as a future improvement.
- **Polling** — rejected: poor latency and higher load for a "live" view.
