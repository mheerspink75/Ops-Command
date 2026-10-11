# OpsCommand Resume and Interview Content

Reusable, verified-only content for presenting OpsCommand on a resume, in a
portfolio, on LinkedIn, and in interviews. Every claim here is grounded in the
repository (code, tests, ADRs, or CI). Nothing here invents users, customers,
production incidents, revenue, team size, performance numbers, or deployment
outcomes. Where a comparison to commercial incident-management tools is made,
it is a **category comparison only** — not an affiliation or equivalence.

## One-line project summary

A full-stack, self-contained incident-response command platform (FastAPI +
React + TypeScript + PostgreSQL + Redis + Celery) with real-time updates,
durable background playbooks, and organization-scoped authorization.

## Two-line portfolio summary

OpsCommand is a production-inspired incident-management platform that gives a
team one calm, live, auditable place to run an incident — status, roles,
timeline, action items, and one-click playbooks — with real-time updates over
WebSockets and durable background execution. It is a complete, tested,
locally-runnable full-stack reference implementation in the same category as
tools like PagerDuty, incident.io, FireHydrant, and Opsgenie (category
comparison only).

## Resume bullets

Four to six concise, verified bullets. Pick the set that matches the role.

- Built a full-stack incident-response platform (FastAPI, SQLAlchemy, Celery,
  React, TypeScript, PostgreSQL, Redis) that gives teams a single live view of
  an incident with real-time updates over WebSockets.
- Designed organization-scoped, server-side authorization with a role
  hierarchy, so no organization can read or write another's data — enforced on
  every route and covered by tests.
- Implemented durable, idempotent background playbook execution with Celery
  and Redis, including retries and real-time progress streamed to the browser
  across processes via a Redis pub/sub bridge.
- Added optimistic concurrency (version + expected_version) and a validated
  state machine so concurrent responders cannot lose updates or make invalid
  status transitions.
- Established a three-level test pyramid (pytest, Vitest + React Testing
  Library, Playwright e2e) plus Ruff, mypy, ESLint, and a CI workflow that
  builds, tests, and scans dependencies.
- Documented significant design decisions in six architecture decision records
  (ADRs) and wrote the security, architecture, and testing reference docs.

## Operations and SRE version

- Focused on the operational core of incident response: a shared, auditable
  command view, explicit incident roles, an append-only timeline, and
  repeatable runbooks.
- Built in observability from the start: structured logging (structlog),
  Prometheus metrics at `/metrics`, optional OpenTelemetry tracing, request-ID
  propagation, and `/health` + `/ready` probes.
- Designed for local reproducibility: a deterministic mock webhook and seeded
  demo data mean playbooks and tests never depend on a paid external service.
- Documented a future deployment path (TLS termination, secret management,
  rate limiting, SSO/MFA) and a rollback checklist.

## Platform Engineering version

- Built a multi-tenant platform with strict organization-scoped data
  isolation and a role-based authorization model enforced server-side.
- Designed a cross-process real-time architecture (in-process hub + Redis
  pub/sub bridge) so background workers can push live updates to connected
  clients.
- Modeled durable background work with idempotency keys, retries with backoff,
  and terminal-status re-checks so duplicate delivery is safe.
- Chose a stateless API (JWT auth) so it can scale across replicas, with Redis
  fanning events out to each.

## Full-Stack Engineering version

- Shipped a complete full-stack application: a typed FastAPI REST + WebSocket
  API, a React + TypeScript + Vite SPA with a typed API client and a WebSocket
  hook, and a Celery worker.
- Enforced quality with Ruff, mypy, ESLint, `tsc`, a three-level test pyramid,
  and a CI workflow that builds and scans dependencies.
- Used TanStack Query for caching/invalidation, Tailwind for styling, and
  Alembic for explicit, reversible migrations.
- Kept the frontend a presentation layer only — all authorization and business
  rules live in the API.

## Technical Support Engineering version

- Built the customer-facing incident workflow end to end: declare an incident,
  attach affected services, assign roles, add timeline updates, run a
  playbook, and export a post-incident report.
- Designed clear, recoverable user flows with a connection indicator,
  transparent token refresh, and readable error states.
- Wrote a step-by-step demo script and a screenshot capture plan so the
  workflow can be demonstrated and reproduced reliably.
- Documented the API with curated REST + WebSocket examples and auto-generated
  OpenAPI docs.

## LinkedIn project description

> **OpsCommand** — a full-stack incident-response command platform I built to
> give engineering teams one calm, live, auditable place to run an incident.
>
> It's in the same category as tools like PagerDuty, incident.io, FireHydrant,
> and Opsgenie (category comparison only). The stack is FastAPI + SQLAlchemy +
> Celery on the backend and React + TypeScript + Vite on the frontend, with
> PostgreSQL for state and Redis for the broker and a cross-process real-time
> bridge.
>
> Things I'm proud of:
> - **Real-time across processes** — a background worker's playbook progress
>   streams live to the browser via a Redis pub/sub bridge.
> - **Durable, idempotent playbooks** — safe to retry, with retries and
>   per-step progress.
> - **Strict tenancy** — organization-scoped, server-side authorization with a
>   role hierarchy.
> - **Concurrency correctness** — optimistic concurrency + a validated state
>   machine.
> - **Quality** — a three-level test pyramid, Ruff/mypy/ESLint, and CI.
>
> It runs locally with no paid services, and the repo includes architecture
> decision records, a demo script, and deployment guidance.

## Architecture interview talking points

- **Layering:** routes → services → models with a strict dependency direction;
  business rules live in services, not route handlers.
- **Real-time seam:** the `RealtimeHub` is the boundary between "something
  changed" and "the browser knows" — in-process delivery plus a Redis pub/sub
  bridge for cross-process delivery.
- **Stateless API:** auth is JWT, so the API scales across replicas; each
  replica runs its own Redis bridge and Redis fans events out.
- **Durable work:** playbook runs are a separate Celery task with idempotency,
  retries, and terminal-status re-checks.
- **Transactions:** each service method is a single transaction; real-time
  publishing happens after commit so clients never see uncommitted state.

## Security interview talking points

- **Server-side authorization:** the frontend is never a security boundary;
  every org-scoped route resolves membership and role.
- **Tenancy:** unknown orgs return 404, non-members 403, so a caller cannot
  probe or access another org's resources by ID.
- **Auth:** Argon2id password hashing, short-lived JWT access tokens, rotating
  revocable refresh tokens, and Redis-backed login throttling.
- **Secrets:** read from the environment, never committed; audit payloads are
  sanitized; a production guard refuses to boot with the insecure default
  secret.
- **Honest gaps:** no SSO/MFA/SCIM, no general rate limiting, at-most-once
  real-time — all documented as known limitations.

## Reliability interview talking points

- **Idempotency:** playbook runs are keyed by an `idempotency_key`; duplicate
  dispatch returns the existing run, and the task re-checks terminal status
  before doing work.
- **Retries:** transient step failures retry with backoff; permanent failures
  stop the run.
- **Concurrency:** optimistic concurrency prevents lost updates; a validated
  state machine prevents invalid transitions.
- **Real-time as optimization:** REST is the source of truth; WebSockets are
  an at-most-once optimization, so a dropped event does not corrupt state.
- **Observability:** structured logs, Prometheus metrics, optional tracing,
  and health/readiness probes.

## Testing interview talking points

- **Three levels:** backend (pytest), frontend unit (Vitest + React Testing
  Library), and end-to-end (Playwright).
- **E2E drives the real stack:** the Playwright test exercises real HTTP +
  WebSocket + background execution, and it mirrors the demo script.
- **Isolation:** backend tests use a transactional fixture that rolls back per
  test; frontend unit tests mock the API client and WebSocket.
- **Quality gates:** Ruff, mypy, ESLint, `tsc`, and a CI workflow that builds
  and scans dependencies.
- **Honesty about results:** the backend and e2e suites require Postgres/Redis
  and a running stack; results are reported as point-in-time, not a standing
  guarantee.

## STAR examples

Each example is based only on verified aspects of the repository.

### Example 1 — Real-time across processes

- **Situation:** The command view had to update the moment anything changed,
  including changes made by a background worker in a separate process.
- **Task:** Deliver worker-generated playbook progress to connected browsers
  without making real-time a correctness dependency.
- **Action:** Built a `RealtimeHub` that delivers in-process and publishes to
  Redis; a bridge thread in the API process subscribes and forwards to
  WebSocket clients. REST remains the source of truth.
- **Result:** Worker progress reaches the browser live; the design is captured
  in ADR-002 and exercised by the WebSocket and worker tests.

### Example 2 — Durable, idempotent playbooks

- **Situation:** Playbook runs are multi-step, may call external endpoints, and
  must survive API restarts and be safe to retry.
- **Task:** Make runs durable and idempotent with retries.
- **Action:** Modeled runs as a Celery task keyed by an `idempotency_key`,
  with retries with backoff and a terminal-status re-check before doing work.
- **Result:** Duplicate dispatch returns the existing run; the behavior is
  covered by the playbook and worker tests and documented in ADR-003.

### Example 3 — Concurrency correctness

- **Situation:** Multiple responders act on the same incident concurrently and
  could silently clobber each other's updates.
- **Task:** Prevent lost updates and invalid state transitions.
- **Action:** Added optimistic concurrency (`Incident.version` +
  `expected_version`) and a validated state machine for status transitions.
- **Result:** Conflicting writes fail loudly (409) instead of dropping data;
  covered by the incident tests and documented in ADR-004.

### Example 4 — Strict tenancy

- **Situation:** The platform is multi-tenant and no organization may access
  another's data, including by guessing resource IDs.
- **Task:** Enforce organization-scoped authorization server-side.
- **Action:** Every org-scoped route resolves membership and role; unknown
  orgs return 404 and non-members 403.
- **Result:** Cross-org access is blocked and covered by the auth and incident
  tests; documented in ADR-001.
