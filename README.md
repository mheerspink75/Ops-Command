# OpsCommand

**OpsCommand** is a full-stack incident-response command platform for small
engineering and on-call teams. When something breaks, responders need one
calm, shared place to coordinate: who is in charge, which services are
affected, what has been tried, and what happens next. OpsCommand gives them
that single live view — incident status and severity, affected services and
their dependencies, assigned roles, a shared timeline, action items, and
one-click playbook execution — with real-time updates over WebSockets and
durable background execution of runbooks.

It is a complete, self-contained reference implementation: a FastAPI +
SQLAlchemy + Celery backend, a React + TypeScript + Vite frontend, PostgreSQL
for state, Redis for caching / pub-sub / the Celery broker, and a
deterministic mock webhook so the whole stack runs locally with no paid
external services.

> **Status:** local development build. This is **not** a production
> deployment and there is **no public live demo**. Quality checks that can run
> without external services pass in this environment (see
> [Verified quality checks](#verified-quality-checks)); the backend test suite
> and end-to-end suite require Postgres/Redis and a running stack. See
> [Known limitations](#known-limitations).

---

## Why this project matters

Incident response is where engineering teams feel the most pressure: a
production problem is live, customers are affected, and the team has to
coordinate quickly under stress. Without a shared system of record, that
coordination happens in chat threads and tribal knowledge — ownership is
ambiguous, context is lost, and the post-incident story is reconstructed
after the fact.

OpsCommand addresses that operational problem by giving a team a single,
live, auditable command view of an incident. It is a **production-inspired
incident-management platform** in the same category as tools such as
**PagerDuty**, **incident.io**, **FireHydrant**, and **Opsgenie**. These are
**category comparisons only** — OpsCommand is not affiliated with, endorsed
by, or equivalent to any of those products, and it does not claim feature
parity with them. The point of the comparison is to make the *problem domain*
immediately recognizable: this is the kind of software teams use to run
incidents.

The value it delivers:

- **Faster, calmer response** — one shared view instead of scattered chat.
- **Explicit ownership** — incident roles (commander, communications,
  operations, scribe) make who-is-doing-what unambiguous.
- **Accountable record** — an append-only, auditable timeline and action
  items support post-incident review.
- **Repeatable actions** — declarative playbooks encode the "what do we do
  next" steps and run them durably in the background.

## Key capabilities

Verified capabilities present in the codebase (each is exercised by tests and
documented in `docs/`):

- **Incident lifecycle management** — declare, investigate, monitor, resolve,
  and close incidents through a validated state machine.
- **Organization-scoped access** — every resource belongs to an organization;
  cross-organization access is blocked server-side.
- **Role-based authorization** — `owner`, `administrator`, `responder`, and
  `viewer` roles with a privilege hierarchy, enforced on every route.
- **Shared timelines** — an append-only, auditable event log per incident.
- **Action-item tracking** — follow-ups with assignees and status.
- **Incident role assignments** — assign commander, communications,
  operations, and scribe to team members.
- **Service dependency tracking** — services, tiers, and upstream /
  downstream dependencies per organization.
- **Automated playbooks** — ordered, declarative runbooks executed durably in
  the background with idempotency, retries, and real-time progress.
- **Real-time updates** — authenticated WebSockets push incident events to
  connected clients, bridged across processes via Redis pub/sub.
- **Audit logging** — an organization-scoped, sanitized audit trail.
- **Post-incident reporting** — generate and download a Markdown report.
- **Observability** — structured logging, Prometheus metrics, and optional
  OpenTelemetry tracing.

## Technical highlights

A summary of the verified technologies and engineering concepts. The
"why" behind each choice is in [Technology choices](#technology-choices).

- **Backend:** FastAPI, SQLAlchemy 2.0, Alembic migrations, Celery workers.
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, TanStack Query.
- **Data & messaging:** PostgreSQL 16, Redis 7 (cache, broker, pub/sub).
- **Real-time:** native WebSockets with an in-process hub + Redis pub/sub
  bridge for cross-process delivery.
- **Security:** JWT access + rotating refresh tokens, Argon2id password
  hashing, RBAC, organization-scoped data isolation, login throttling.
- **Delivery & quality:** Docker Compose, a three-level test pyramid
  (pytest, Vitest, Playwright), Ruff, mypy, ESLint, and a CI workflow.
- **Observability:** structlog, Prometheus metrics, optional OpenTelemetry.

## Architecture snapshot

OpsCommand is a three-tier system. A React SPA talks to a versioned FastAPI
REST API and subscribes to incident WebSockets. The API owns all
authorization and business rules and writes to PostgreSQL. A separate Celery
worker executes playbook runs durably and streams progress back to the API
over Redis pub/sub, which the API bridges to connected browsers.

```mermaid
flowchart LR
    subgraph Client
        UI[React SPA<br/>Vite + TS + Tailwind]
    end

    subgraph API[FastAPI backend]
        REST[REST /api/v1]
        WS[WebSocket rooms]
        HUB[RealtimeHub]
        SVC[Domain services]
    end

    subgraph Worker[Celery worker]
        TASK[execute_playbook_run]
    end

    PG[(PostgreSQL)]
    RD[(Redis)]
    WH[mock-webhook]

    UI -- "HTTPS REST" --> REST
    UI -- "WSS" --> WS
    REST --> SVC
    SVC --> PG
    SVC --> HUB
    HUB --> WS
    REST -- "dispatch" --> RD
    RD -- "task queue" --> TASK
    TASK --> PG
    TASK -- "publish progress" --> RD
    RD -- "pub/sub bridge" --> HUB
    TASK -- "webhook step" --> WH
    SVC -- "throttle / tokens" --> RD
```

The detailed request and real-time flows are in
[Architecture overview](#architecture-overview).

## Demo preview

> **No screenshots are included yet.** Authentic captures have not been taken
> in this environment (no browser / display tooling was available). Rather
> than ship placeholder images, this repository provides a step-by-step
> **screenshot capture plan** so real, current captures can be produced and
> dropped in. See [`docs/screenshots/README.md`](docs/screenshots/README.md).

When captures are available, the intended preview is:

1. Login screen
2. Incident dashboard
3. Incident detail (command view)
4. Incident timeline
5. Real-time update activity
6. Playbook execution progress
7. Metrics / observability view
8. Post-incident report workflow

A guided, recruiter-facing walkthrough is in
[`docs/demo-script.md`](docs/demo-script.md), and a recording checklist is in
[`docs/demo-video-checklist.md`](docs/demo-video-checklist.md).

## Quick start

The fastest path to the full application locally is Docker Compose:

```bash
cp .env.example .env
docker compose up --build
```

Then open <http://localhost:5173> and sign in with a demo account (see
[Seed data](#seed-data)). The backend entrypoint applies migrations before
starting the API; run `docker compose exec backend python -m app.seed` (or
`make seed`) to load the demo organization, users, services, incidents, and
playbook.

For a manual, service-by-service setup (Python venv, Node, Postgres + Redis
via Docker, the Celery worker, and the Vite dev server), see
[Local setup](#local-setup).

## Verified quality checks

Checks that were **executed and passed in this environment** (no external
services required):

| Check | Command | Result |
|-------|---------|--------|
| Backend lint (Ruff) | `cd backend && python -m ruff check .` | pass |
| Backend format (Ruff) | `cd backend && python -m ruff format --check .` | pass |
| Backend types (mypy) | `cd backend && python -m mypy app` | pass |
| Frontend lint (ESLint) | `cd frontend && npm run lint` | pass |
| Frontend types (tsc) | `cd frontend && npm run typecheck` | pass |
| Frontend unit tests (Vitest) | `cd frontend && npm test -- --run` | 63 passed |
| Frontend production build | `cd frontend && npm run build` | pass |

**Not run in this environment** (they require Postgres/Redis and a running
stack, which were unavailable): the backend pytest suite and the Playwright
end-to-end suite. Their commands and the conditions under which they were
last verified are in [Testing](#testing). No coverage percentages,
performance numbers, or production metrics are claimed anywhere in this
repository.

---

## Table of contents

- [Why this project matters](#why-this-project-matters)
- [Key capabilities](#key-capabilities)
- [Technical highlights](#technical-highlights)
- [Architecture snapshot](#architecture-snapshot)
- [Demo preview](#demo-preview)
- [Quick start](#quick-start)
- [Verified quality checks](#verified-quality-checks)
- [Architecture overview](#architecture-overview)
- [Technology choices](#technology-choices)
- [Repository layout](#repository-layout)
- [Local setup](#local-setup)
- [Docker setup](#docker-setup)
- [Environment-variable reference](#environment-variable-reference)
- [Migrations](#migrations)
- [Seed data](#seed-data)
- [Testing](#testing)
- [API documentation](#api-documentation)
- [WebSocket design](#websocket-design)
- [Background-worker design](#background-worker-design)
- [Security model](#security-model)
- [Observability](#observability)
- [Screenshots](#screenshots)
- [Known limitations](#known-limitations)
- [Future improvements](#future-improvements)
- [Further documentation](#further-documentation)

---

## Architecture overview

The component diagram is in [Architecture snapshot](#architecture-snapshot).
This section explains the two flows that matter most: a REST request, and a
real-time event that crosses process boundaries.

OpsCommand is a three-tier system:

1. **Frontend** — a React single-page app (Vite + TypeScript + Tailwind) that
   talks to the REST API and subscribes to incident WebSockets.
2. **Backend API** — a FastAPI service exposing a versioned REST API
   (`/api/v1`), health/readiness/metrics endpoints, and authenticated
   WebSocket rooms. It owns all authorization and business rules.
3. **Background worker** — a Celery worker (Redis broker) that executes
   playbook runs durably, publishing progress back to the API via Redis pub/sub.

State lives in **PostgreSQL**; **Redis** provides the Celery broker, the
login-throttle store, and the cross-process event bridge.

### Request flow (REST)

```
Client → FastAPI (auth dependency) → OrgContext (membership + role)
     → domain service (business rules, transaction) → SQLAlchemy → Postgres
     → serializer → JSON response
     → RealtimeHub.publish → (in-process subscribers + Redis pub/sub)
```

### Real-time flow (cross-process)

```
API mutation  → hub.publish(incident_id, event)
                 ├─ in-process subscribers (same API process)
                 └─ Redis PUBLISH opscommand:incident:<id>
Worker step   → hub.publish(...) → Redis PUBLISH
API bridge    → Redis PSUBSCRIBE opscommand:incident:* → forward to WS clients
```

## Technology choices

| Layer            | Choice                                   | Why |
|------------------|------------------------------------------|-----|
| API framework    | **FastAPI**                              | Async, typed, auto OpenAPI docs, first-class WebSockets. |
| ORM / migrations | **SQLAlchemy 2.0** + **Alembic**         | Mature, explicit migrations, typed models. |
| Database         | **PostgreSQL 16**                        | Relational integrity, JSONB, strong concurrency. |
| Cache / broker   | **Redis 7**                              | Login throttling, Celery broker, cross-process pub/sub. |
| Background jobs  | **Celery**                               | Durable, retriable task execution with a Redis broker. |
| Auth             | **JWT** (access + rotating refresh) + **Argon2** | Stateless access tokens, strong password hashing. |
| Frontend         | **React 18 + TypeScript + Vite**         | Fast dev loop, typed, component model. |
| Styling          | **Tailwind CSS**                         | Utility-first, no CSS-in-JS runtime cost. |
| Data fetching    | **TanStack Query**                       | Caching, retries, and invalidation for REST. |
| Real-time        | **Native WebSocket**                     | Low-latency incident updates with heartbeats. |
| Testing          | **pytest**, **Vitest + RTL**, **Playwright** | Backend, frontend unit, and end-to-end coverage. |
| Lint / types     | **Ruff**, **mypy**, **ESLint**, **tsc**  | Fast, consistent quality gates. |
| Observability    | **structlog**, **Prometheus**, **OpenTelemetry** | Structured logs, metrics, optional tracing. |

## Repository layout

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST + WebSocket route handlers
│   │   ├── core/            # errors, ids, pagination, redis, sanitize, audit
│   │   ├── db/              # SQLAlchemy models + session
│   │   ├── observability/   # logging, metrics, otel
│   │   ├── realtime/        # RealtimeHub (in-process + Redis bridge)
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── security/        # auth, tokens, passwords, throttling
│   │   ├── services/        # domain logic (incidents, playbooks, reports, …)
│   │   ├── worker/          # Celery broker + tasks
│   │   ├── config.py        # settings (env-driven)
│   │   ├── main.py          # app factory + middleware
│   │   └── seed.py          # idempotent demo data
│   ├── alembic/             # migrations
│   ├── tests/               # backend test suite
│   ├── Dockerfile
│   ├── scripts/entrypoint.sh
│   └── pyproject.toml
├── frontend/
│   ├── e2e/                 # Playwright end-to-end tests
│   ├── src/
│   │   ├── api/             # typed REST client
│   │   ├── auth/            # auth context
│   │   ├── components/      # shared UI components
│   │   ├── org/             # organization context
│   │   ├── pages/           # Dashboard, IncidentList, IncidentDetail, Metrics
│   │   ├── realtime/        # WebSocket hook
│   │   └── styles/
│   ├── Dockerfile
│   └── package.json
├── mock-webhook/            # deterministic webhook target for playbooks
├── docker-compose.yml
├── Makefile
├── .env.example
└── docs/                    # architecture, security, testing, ADRs
```

## Local setup

Prerequisites: **Python 3.12+**, **Node 20+**, **Docker** (for Postgres +
Redis), and the Playwright browsers for e2e tests.

### 1. Start infrastructure

```bash
docker compose up -d postgres redis
```

Postgres is exposed on host port **5433** (to avoid clashing with a local
Postgres on 5432). Redis on **6379**.

### 2. Backend

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e "backend[dev]"

# Configure environment (see .env.example)
cp .env.example .env

# Apply migrations and seed demo data
cd backend
python -m alembic upgrade head
python -m app.seed
cd ..

# Run the API
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Background worker (required for playbook execution)

```bash
cd backend
python -m celery -A app.worker.broker:celery_app worker --loglevel=info
```

> **Windows note:** the default Celery spawn pool can hit a
> `PermissionError: [WinError 5]` in some environments. If you see pool
> workers crashing, run with `--pool=solo` to execute tasks in the main
> process.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Set `VITE_API_BASE_URL=http://localhost:8000` and
`VITE_WS_URL=ws://localhost:8000` (see `.env.example` / `frontend/.env.local`).

### 5. Open the app

Visit <http://localhost:5173> and sign in with a demo account (see
[Seed data](#seed-data)).

## Docker setup

The full stack (Postgres, Redis, mock-webhook, backend, worker, frontend) is
defined in `docker-compose.yml`.

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: <http://localhost:5173>
- API: <http://localhost:8000> (docs at <http://localhost:8000/docs>)
- mock-webhook: <http://localhost:9000>

The backend entrypoint runs migrations before starting the API. The worker
service runs the Celery worker.

## Environment-variable reference

All backend configuration is environment-driven (see `backend/app/config.py`
and `.env.example`).

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | `development` / `production`. |
| `DEBUG` | `true` | Enables debug logging; disables JSON logs. |
| `APP_NAME` | `OpsCommand` | Service name shown in responses. |
| `SECRET_KEY` | `insecure-dev-secret-change-me` | **Required to be strong in production.** Used to sign JWTs. |
| `ENFORCE_SECURE_SECRET` | `true` | Refuse to boot in production with the insecure default secret. |
| `ACCESS_TOKEN_TTL_SECONDS` | `900` | Access-token lifetime. |
| `REFRESH_TOKEN_TTL_SECONDS` | `1209600` | Refresh-token lifetime (14 days). |
| `DATABASE_URL` | `postgresql+psycopg://opscommand:opscommand@localhost:5433/opscommand` | Postgres DSN. |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL (cache, throttle, broker, pub/sub). |
| `LOGIN_MAX_ATTEMPTS` | `5` | Failed logins allowed per identifier per window. |
| `LOGIN_WINDOW_SECONDS` | `60` | Throttle window length. |
| `CORS_ORIGINS` | `["http://localhost:5173","http://localhost:3000"]` | Allowed origins (JSON array). |
| `OTEL_ENABLED` | `true` | Enable OpenTelemetry tracing. |
| `OTEL_EXPORTER_ENDPOINT` | `http://localhost:4317` | OTLP gRPC endpoint. |
| `METRICS_ENABLED` | `true` | Expose `/metrics`. |

Frontend (Vite) variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | REST base URL. |
| `VITE_WS_URL` | `ws://localhost:8000` | WebSocket base URL. |

## Migrations

Migrations are managed with Alembic.

```bash
cd backend
python -m alembic upgrade head        # apply all migrations
python -m alembic downgrade -1        # roll back one revision
python -m alembic current             # show current revision
python -m alembic revision --autogenerate -m "describe change"  # new revision
```

## Seed data

`python -m app.seed` is **idempotent** and creates a demo organization
(**Acme Operations**, slug `acme-ops`) with:

- One user per role (all share the same non-production password):

  | Email | Role |
  |-------|------|
  | `owner@acme-ops.io` | owner |
  | `admin@acme-ops.io` | administrator |
  | `responder@acme-ops.io` | responder |
  | `viewer@acme-ops.io` | viewer |

  **Password for all demo users:** `Demo-Password-123!`

- Four services: `checkout-api` (critical), `orders-database` (critical),
  `session-cache` (standard), `event-queue` (standard), with dependencies.
- An active incident (**Checkout latency spike**, SEV2, investigating) and a
  resolved incident (**Cache eviction storm**, SEV3).
- A sample playbook (**Standard escalation**) with timeline, action-item,
  status-change, wait, and snapshot steps.

> These credentials are for local demonstration only. Do not use them in any
> real deployment.

## Testing

| Suite | Command |
|-------|---------|
| Backend (pytest) | `cd backend && python -m pytest -q` |
| Frontend unit (Vitest + RTL) | `cd frontend && npm test -- --run` |
| End-to-end (Playwright) | `cd frontend && npm run e2e` |
| Backend lint (Ruff) | `cd backend && python -m ruff check .` |
| Backend types (mypy) | `cd backend && python -m mypy app` |
| Frontend lint (ESLint) | `cd frontend && npm run lint` |
| Frontend types (tsc) | `cd frontend && npm run typecheck` |
| Frontend build | `cd frontend && npm run build` |

The `Makefile` provides `make test`, `make lint`, `make typecheck`, and
`make verify` (lint + typecheck + tests) as convenience targets.

**Results and how to reproduce them.** The checks that do not require
external services were executed and passed in this environment: backend
Ruff (lint + format) and mypy, and frontend ESLint, `tsc`, Vitest (63
tests), and the production build. The backend pytest suite and the Playwright
end-to-end suite require Postgres/Redis and a running stack; in the documented
development environment they last reported **96 backend tests passing** and
**2 end-to-end tests passing**. Those two numbers are point-in-time results
from that environment, not a standing guarantee and not a CI-enforced
threshold. No coverage percentages or performance metrics are claimed.

## API documentation

- **Interactive OpenAPI docs:** <http://localhost:8000/docs> (Swagger UI)
- **OpenAPI JSON:** <http://localhost:8000/openapi.json>
- **Curated examples:** [`docs/api-examples.md`](docs/api-examples.md)

All org-scoped routes are namespaced under
`/api/v1/organizations/{org_id}/...`. Health, readiness, and metrics are at
the root: `/health`, `/ready`, `/metrics`.

## WebSocket design

Clients subscribe to an incident room:

```
ws://localhost:8000/ws/incidents/{incident_id}?token=<access_token>
```

- **Authorization** happens at connect time: the access token is verified and
  the caller's membership in the incident's organization is checked.
  Unauthorized connections are closed with code `4401` before the socket is
  accepted.
- **Events** are JSON messages with a `type` field, e.g. `incident_created`,
  `incident_updated`, `status_changed`, `role_assigned`, `timeline_event`,
  `action_item`, `playbook_progress`, plus `connected` and `ping` heartbeats.
- **Cross-process delivery:** the `RealtimeHub` delivers to in-process
  subscribers and also publishes to Redis (`opscommand:incident:<id>`). A
  bridge thread in the API process subscribes to that pattern and forwards
  events to connected clients, so a worker's playbook progress reaches the
  browser even though it runs in a separate process.
- **Heartbeats:** an application-level `ping` is sent every 25 s to keep
  proxies and clients alive.

## Background-worker design

Playbooks execute in a **Celery** worker using Redis as the broker and result
backend.

- **Dispatch:** `POST /api/v1/organizations/{org_id}/incidents/{incident_id}/playbook-runs`
  creates a `PlaybookRun` row (status `pending`) and enqueues
  `execute_playbook_run`.
- **Idempotency:** runs are keyed by an `idempotency_key`; a duplicate
  dispatch returns the existing run instead of re-executing. The task also
  checks terminal status before doing work, so duplicate delivery is safe.
- **Retries:** transient step failures (e.g. a webhook call) retry with
  exponential backoff up to a maximum; permanent failures stop the run.
- **Progress:** each step's result is persisted and published in real time via
  the `RealtimeHub`, so the UI updates live.
- **Safety:** failure details never include secrets; webhook targets are the
  deterministic `mock-webhook` service in local development.

## Security model

- **Server-side authorization.** The frontend is never a security boundary.
  Every org-scoped route resolves the caller's membership and role before any
  data is returned. Cross-organization access via URL identifiers is blocked
  (404 for unknown orgs, 403 for non-members).
- **Role hierarchy.** `viewer < responder < administrator < owner`. Read
  access requires membership; write actions require at least `responder`.
- **Passwords.** Hashed with **Argon2id**.
- **Tokens.** Short-lived JWT **access** tokens (15 min) plus rotating
  **refresh** tokens (14 days) stored server-side and revocable on logout.
- **Login throttling.** Per-identifier failed-login throttling backed by
  Redis (default 5 attempts / 60 s).
- **Production guard.** The app refuses to start in production with the
  insecure default `SECRET_KEY`.
- **Audit log.** Organization-scoped, append-only, with sanitized payloads
  (secrets and sensitive fields are redacted).
- **CORS** is restricted to configured origins.

See [`docs/security.md`](docs/security.md) for details and
[`docs/decisions/`](docs/decisions/) for the architectural decisions behind
these choices.

## Observability

- **Structured logging** via `structlog` (JSON in non-debug mode).
- **Prometheus metrics** at `/metrics` (HTTP request counts/durations, active
  WebSocket connections, worker task outcomes).
- **OpenTelemetry** tracing (optional, `OTEL_ENABLED`).
- **Request IDs** are propagated via the `X-Request-ID` header and included
  in logs and responses for correlation.
- **Health probes:** `/health` (liveness) and `/ready` (checks Postgres +
  Redis).

## Screenshots

> **No screenshots are included yet.** Authentic captures have not been taken
> in this environment (no browser / display tooling was available). Rather
> than ship placeholder images, this repository provides a step-by-step
> **screenshot capture plan** so real, current captures can be produced and
> dropped in. See [`docs/screenshots/README.md`](docs/screenshots/README.md).

The intended captures (login, dashboard, incident detail, timeline, real-time
activity, playbook run, metrics, and post-incident report) are listed with
exact steps, required demo state, and recommended dimensions in that plan.

## Known limitations

- **Single-region, single-tenant-per-org** model; there is no cross-org
  federation or global search.
- **Playbook steps** are a fixed, declarative set (timeline message, action
  item, status change, wait, mock webhook, snapshot). There is no arbitrary
  scripting or external service integration beyond the mock webhook.
- **Real-time** delivery relies on Redis pub/sub; it is at-most-once and not
  a durable message queue. Clients should treat REST as the source of truth
  and WebSockets as an optimization.
- **No rate limiting** on general API routes (only login is throttled).
- **No SSO / MFA / SCIM**; authentication is email + password with JWT.
- **Reports** are generated on demand and not stored as first-class entities.
- **Windows Celery** may require `--pool=solo` (see Local setup).
- **No automated coverage reporting** is configured; test counts above are
  from the local environment, not a CI-enforced threshold.

## Future improvements

- Durable, at-least-once event delivery (e.g. a message queue with
  acknowledgement) and event replay.
- SSO (OIDC/SAML), MFA, and session management.
- Playbook authoring UI with a visual step editor and validation.
- Alerting integrations (PagerDuty, Opsgenie, Slack) as first-class playbook
  steps.
- Global search, saved views, and incident templates.
- Coverage thresholds and mutation testing in CI.
- Horizontal scaling guidance (stateless API, multiple workers) and load
  testing.

## Further documentation

Technical reference:

- [`docs/architecture.md`](docs/architecture.md) — deep dive on components and data flow
- [`docs/security.md`](docs/security.md) — security model and threat considerations
- [`docs/testing.md`](docs/testing.md) — testing strategy and how to run each suite
- [`docs/api-examples.md`](docs/api-examples.md) — curated REST + WebSocket examples
- [`docs/decisions/`](docs/decisions/) — architecture decision records (ADRs)

Demonstration and portfolio:

- [`docs/demo-script.md`](docs/demo-script.md) — a recruiter-facing walkthrough of the incident workflow
- [`docs/demo-video-checklist.md`](docs/demo-video-checklist.md) — how to record and publish a demo video
- [`docs/screenshots/README.md`](docs/screenshots/README.md) — screenshot capture plan
- [`docs/deployment-options.md`](docs/deployment-options.md) — how to run this beyond a laptop (future/optional path)
- [`docs/resume-project-entry.md`](docs/resume-project-entry.md) — reusable resume and interview content
- [`docs/portfolio-showcase.md`](docs/portfolio-showcase.md) — a portfolio case study
- [`docs/portfolio-audit.md`](docs/portfolio-audit.md) — the portfolio audit that motivated these changes
- [`docs/recruiter-impact-review.md`](docs/recruiter-impact-review.md) — a transparent before/after impact review
