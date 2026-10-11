# OpsCommand Portfolio Showcase

A reusable case study for OpsCommand. This document is written to be dropped
into a personal portfolio website, a GitHub Pages page, a LinkedIn article, a
job application, or interview preparation. Every technical claim is grounded in
the repository. Links that do not exist yet are marked **TODO**.

## Executive summary

OpsCommand is a full-stack, self-contained incident-response command platform
I built to give engineering teams one calm, live, auditable place to run an
incident. It is a production-inspired incident-management platform in the same
category as tools like PagerDuty, incident.io, FireHydrant, and Opsgenie
(category comparison only — not an affiliation or equivalence). The stack is
FastAPI + SQLAlchemy + Celery on the backend and React + TypeScript + Vite on
the frontend, with PostgreSQL for state and Redis for the broker and a
cross-process real-time bridge. It runs locally with no paid external services,
is covered by a three-level test pyramid and CI, and is documented with
architecture decision records.

## The problem

When a production incident is live, a team has to coordinate quickly under
pressure: who is in charge, which services are affected, what has been tried,
and what happens next. Without a shared system of record, that coordination
happens in chat threads and tribal knowledge — ownership is ambiguous, context
is lost, and the post-incident story is reconstructed after the fact. The
result is slower resolution, duplicated work, and a weaker learning loop.

## The solution

OpsCommand gives a team a single, live, auditable command view of an incident:

- **Status and severity** with a validated state machine.
- **Affected services and their dependencies.**
- **Explicit incident roles** (commander, communications, operations, scribe).
- **A shared, append-only timeline** and **action items**.
- **One-click playbooks** that run durably in the background with real-time
  progress.
- **Real-time updates** over WebSockets, bridged across processes.
- **Post-incident reports** generated on demand from the same source of truth.

## Target users

- Small engineering and on-call teams that need to coordinate incident
  response.
- Responders who want a single live view instead of scattered chat.
- Engineering leaders who want an auditable record and repeatable runbooks.

## Key capabilities

- Incident lifecycle management (declare → investigate → monitor → resolve →
  close).
- Organization-scoped access with server-side authorization.
- Role-based access control (owner, administrator, responder, viewer).
- Shared timelines and action-item tracking.
- Incident role assignments.
- Service dependency tracking.
- Automated, durable playbooks with idempotency and retries.
- Real-time updates over WebSockets.
- Audit logging with sanitized payloads.
- Post-incident reporting.
- Observability (structured logging, Prometheus metrics, optional tracing).

## Architecture overview

A three-tier system:

- **Frontend** — a React SPA (Vite + TypeScript + Tailwind) that talks to the
  REST API and subscribes to incident WebSockets.
- **Backend API** — a FastAPI service exposing a versioned REST API,
  health/readiness/metrics endpoints, and authenticated WebSocket rooms. It
  owns all authorization and business rules.
- **Background worker** — a Celery worker (Redis broker) that executes
  playbook runs durably and streams progress back to the API via Redis pub/sub.

State lives in PostgreSQL; Redis provides the Celery broker, the login-throttle
store, and the cross-process event bridge. See
[`architecture.md`](architecture.md) for the deep dive.

## Real-time event flow

The `RealtimeHub` is the seam between "something changed" and "the browser
knows about it":

- **In-process:** `subscribe` / `publish` deliver events to callbacks in the
  same process.
- **Cross-process:** `publish` also does a Redis `PUBLISH` to
  `opscommand:incident:<id>`. A daemon thread in the API process runs a
  `PSUBSCRIBE opscommand:incident:*` loop and forwards matching messages to
  in-process subscribers. This is what lets a **worker** process publish
  playbook progress that an **API** process then pushes to the browser.
- **Failure isolation:** a throwing subscriber is caught and logged; Redis is
  optional (in-process delivery still works if Redis is down).

REST remains the source of truth; real-time is an at-most-once optimization.
See ADR-002.

## Background job execution

Playbooks execute in a Celery worker using Redis as the broker and result
backend:

- **Dispatch:** a `PlaybookRun` row (status `pending`) is created and
  `execute_playbook_run` is enqueued.
- **Idempotency:** runs are keyed by an `idempotency_key`; a duplicate
  dispatch returns the existing run, and the task re-checks terminal status
  before doing work.
- **Retries:** transient step failures retry with exponential backoff;
  permanent failures stop the run.
- **Progress:** each step's result is persisted and published in real time via
  the `RealtimeHub`.
- **Safety:** failure details never include secrets; webhook targets are the
  deterministic `mock-webhook` service in local development.

See ADR-003 and ADR-006.

## Security model

- **Server-side authorization** on every route; the frontend is never a
  security boundary.
- **Role hierarchy:** `viewer < responder < administrator < owner`.
- **Passwords** hashed with Argon2id.
- **Tokens:** short-lived JWT access tokens plus rotating, revocable refresh
  tokens.
- **Login throttling** backed by Redis.
- **Production guard** that refuses to start with the insecure default secret.
- **Audit log** that is organization-scoped, append-only, and sanitized.
- **CORS** restricted to configured origins.

See [`security.md`](security.md) and ADR-001, ADR-005.

## Observability

- **Structured logging** via structlog (JSON in non-debug mode).
- **Prometheus metrics** at `/metrics` (HTTP request counts/durations, active
  WebSocket connections, worker task outcomes).
- **OpenTelemetry** tracing (optional).
- **Request IDs** propagated via `X-Request-ID` and included in logs and
  responses.
- **Health probes:** `/health` (liveness) and `/ready` (Postgres + Redis).

## Testing strategy

A three-level test pyramid:

- **Backend (pytest):** API, services, auth, worker, audit, reports, export,
  WebSocket, and health.
- **Frontend unit (Vitest + React Testing Library):** pages, components,
  contexts, hooks, and the API client.
- **End-to-end (Playwright):** the full incident workflow against the real
  stack.

Quality gates: Ruff, mypy, ESLint, `tsc`, and a CI workflow that builds and
scans dependencies. See [`testing.md`](testing.md).

## Technical challenges

- **Real-time across processes:** delivering a worker's progress to the
  browser required a cross-process bridge (Redis pub/sub) rather than a
  single-process in-memory pub/sub.
- **Durable, idempotent background work:** making playbook runs survive
  restarts and be safe to retry required idempotency keys, retries, and
  terminal-status re-checks.
- **Concurrency correctness:** preventing lost updates and invalid transitions
  required optimistic concurrency and a validated state machine.
- **Strict tenancy:** blocking cross-org access, including by ID guessing,
  required server-side membership + role resolution on every route.

## Engineering decisions

Six architecture decision records capture the significant choices and their
trade-offs:

- **ADR-001** — Organization-scoped, server-side authorization.
- **ADR-002** — Real-time delivery via in-process hub + Redis pub/sub bridge.
- **ADR-003** — Durable playbook execution with Celery + idempotency.
- **ADR-004** — Optimistic concurrency for incident mutations.
- **ADR-005** — JWT access/refresh tokens with Argon2 password hashing.
- **ADR-006** — Deterministic mock webhook for self-contained playbooks.

See [`decisions/`](decisions/).

## Key accomplishments

- A complete, working full-stack application that runs locally with no paid
  services.
- A cross-process real-time architecture that streams background-worker
  progress to the browser.
- Durable, idempotent, retriable playbook execution.
- Strict organization-scoped authorization with a role hierarchy.
- Optimistic concurrency and a validated state machine.
- A three-level test pyramid, lint/type gates, and CI.
- Six ADRs and a full set of reference docs (architecture, security, testing,
  API examples).

## Known limitations

- Single-region, single-tenant-per-org; no cross-org federation or global
  search.
- Playbook steps are a fixed, declarative set; no arbitrary scripting.
- Real-time delivery is at-most-once (Redis pub/sub), not a durable queue.
- No general API rate limiting (only login is throttled).
- No SSO / MFA / SCIM.
- Reports are generated on demand and not stored as first-class entities.
- No automated coverage reporting is configured.

## Lessons learned

- Framing the **business problem first** (incident coordination under
  pressure) made the architecture decisions easier to justify.
- Treating **real-time as an optimization**, not a correctness dependency,
  kept the system honest and simpler.
- Writing **ADRs at decision time** made the "why" available later, which is
  exactly what an interviewer or reviewer asks for.
- Keeping the **frontend a presentation layer only** made the security model
  clearer and the API the single source of truth.
- Being **explicit about limitations** reads as senior and builds trust.

## Future enhancements

- Durable, at-least-once event delivery and event replay.
- SSO (OIDC/SAML), MFA, and session management.
- A playbook authoring UI with a visual step editor and validation.
- Alerting integrations (PagerDuty, Opsgenie, Slack) as first-class playbook
  steps.
- Global search, saved views, and incident templates.
- Coverage thresholds and mutation testing in CI.
- Horizontal scaling guidance and load testing.

## Repository and demo links

- **Repository:** <https://github.com/mheerspink75/Ops-Command>
- **Live demo:** TODO — no public live deployment exists yet; see
  [`deployment-options.md`](deployment-options.md) for a future/optional path.
- **Demo video:** TODO — not recorded yet; see
  [`demo-video-checklist.md`](demo-video-checklist.md).
- **Screenshots:** TODO — not captured yet; see
  [`screenshots/README.md`](screenshots/README.md).
- **Demo script:** [`demo-script.md`](demo-script.md)
- **Architecture decision records:** [`decisions/`](decisions/)
