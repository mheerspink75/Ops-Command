# Architecture

This document is a deep dive into how OpsCommand is put together. For a
high-level overview and the component diagram, see the
[README](../README.md#architecture-overview).

## Goals

- **Correctness under concurrency.** Multiple responders act on the same
  incident at the same time; the system must not lose updates or allow
  invalid state transitions.
- **Real-time feel.** The command view updates the moment anything changes,
  including changes made by a background worker in a separate process.
- **Durable background work.** Playbook runs must survive API restarts and be
  safe to retry.
- **Strong tenancy.** No organization can read or write another organization's
  data.
- **Local-first.** The entire stack runs on a laptop with no paid external
  services.

## Component responsibilities

### Frontend (React SPA)

- **`src/api/client.ts`** — a single typed REST client. Every API call goes
  through here, including a centralized 401 handler that refreshes the access
  token (and, for non-auth endpoints, redirects to login).
- **`src/auth/AuthContext.tsx`** — owns the token pair, login/logout, and
  automatic refresh.
- **`src/org/OrgContext.tsx`** — the active organization and its membership.
- **`src/realtime/useIncidentSocket.ts`** — a hook that opens the incident
  WebSocket, reconnects, and exposes live events to components.
- **Pages** — `Dashboard`, `IncidentList`, `IncidentDetail`, `Metrics`.
  `IncidentDetail` is the command view: status, roles, timeline, action items,
  and playbook execution.

The frontend is a **presentation layer only**. It never makes authorization
decisions; it relies on the API to enforce them.

### Backend API (FastAPI)

Layered, with a strict dependency direction (routes → services → models):

- **`api/v1/*`** — thin route handlers. They parse/validate input (Pydantic),
  resolve the `OrgContext` (auth + role), call a domain service, serialize the
  result, and publish a real-time event. They contain no business rules.
- **`services/*`** — the domain logic and transaction boundaries. This is
  where business rules (state machine, concurrency, idempotency) live.
- **`db/models/*`** — SQLAlchemy models.
- **`schemas/*`** — Pydantic request/response models.
- **`security/*`** — auth dependencies, token handling, password hashing,
  throttling.
- **`core/*`** — cross-cutting utilities: error types, request IDs,
  pagination, Redis client, sanitization, audit.
- **`realtime/hub.py`** — the `RealtimeHub` (see below).
- **`main.py`** — the app factory: middleware (CORS, request context, metrics),
  error handlers, and the lifespan that starts/stops the Redis bridge.

### Background worker (Celery)

- **`worker/broker.py`** — the Celery app (Redis broker + backend).
- **`worker/tasks.py`** — `execute_playbook_run`, the single durable task. It
  opens a DB session, calls `playbook_service.execute_run`, and records
  metrics.

### RealtimeHub

The `RealtimeHub` is the seam between "something changed" and "the browser
knows about it."

- **In-process:** `subscribe(incident_id, callback)` / `publish(incident_id,
  event)` deliver events to callbacks registered in the same process.
- **Cross-process:** `publish` also does a Redis `PUBLISH` to
  `opscommand:incident:<id>`. A daemon thread (`start_redis_bridge`) runs a
  `PSUBSCRIBE opscommand:incident:*` loop and forwards matching messages to
  the in-process subscribers. This is what lets a **worker** process publish
  playbook progress that an **API** process then pushes to the browser.
- **Failure isolation:** a throwing subscriber is caught and logged so one bad
  consumer cannot break the others; Redis is optional (in-process delivery
  still works if Redis is down).

### mock-webhook

A tiny deterministic HTTP service (stdlib `http.server`) that echoes back the
payload it receives. It is the target of the `mock_webhook` playbook step so
that playbooks and tests are fully self-contained and reproducible.

## Data model

Core entities (see `backend/app/db/models/`):

- **Organization** — the tenancy boundary.
- **User** — a person (email, username, Argon2 password hash).
- **Membership** — links a user to an organization with a role.
- **Service** — a monitored service (name, tier, status).
- **ServiceDependency** — upstream → downstream edges.
- **Incident** — the central entity (title, severity, status, version,
  commander, created_by).
- **IncidentService** — incident ↔ service.
- **IncidentRoleAssignment** — incident role (commander, communications,
  operations, scribe) ↔ user.
- **TimelineEvent** — append-only event log.
- **ActionItem** — follow-up task.
- **Playbook** — ordered steps (JSON).
- **PlaybookRun** — a durable execution of a playbook (status, progress,
  idempotency key).
- **AuditLog** — organization-scoped audit trail.
- **RefreshToken** — server-side refresh tokens.

## Concurrency model

- **Optimistic concurrency** on incident mutations. `Incident.version` is
  incremented on each write; a mutation supplies `expected_version` and fails
  with a conflict if it does not match the current row. This prevents two
  responders from clobbering each other's status changes.
- **State machine.** `incident_service.VALID_TRANSITIONS` defines the allowed
  status graph; invalid transitions are rejected.
- **Idempotent playbook runs.** A run is keyed by `idempotency_key`; duplicate
  dispatch returns the existing run, and the task re-checks terminal status
  before doing work.
- **Retries with backoff.** Transient step failures retry; permanent failures
  stop the run.

## Transactions

Each domain service method is a single transaction (via `session_scope` or the
request-scoped session). Real-time publishing happens **after** the commit so
clients never observe uncommitted state.

## Scaling notes

- The API is stateless (auth is JWT; the only in-memory state is the
  `RealtimeHub` subscriber set, which is per-process by design).
- Multiple API replicas each run their own Redis bridge; Redis pub/sub fans
  events out to all of them.
- Multiple workers can run in parallel; idempotency and the DB are the
  coordination points.
