# OpsCommand Deployment Options

This document describes how OpsCommand **could** be run beyond a laptop. It is
a **future / optional deployment path**, not a description of a live system.

> **Current status: local-only.** There is **no public live deployment** of
> OpsCommand and **no public URL**. Nothing in this repository has been
> deployed to a shared or production environment. This document is guidance
> for anyone who wants to stand the stack up on their own infrastructure.

## Current deployment status

- The project runs as a **local development stack** via Docker Compose
  (`docker-compose.yml`) or manually (see README → [Local
  setup](../README.md#local-setup)).
- All services (Postgres, Redis, mock-webhook, backend, worker, frontend) run
  on the developer's machine.
- There is no managed hosting, no public endpoint, and no shared
  credentials.
- The CI workflow (`.github/workflows/ci.yml`) builds and tests the code but
  does **not** deploy it anywhere.

## Deployment requirements

The verified infrastructure requirements (from `docker-compose.yml`,
`backend/pyproject.toml`, and `frontend/package.json`):

- **PostgreSQL 16** — primary state store.
- **Redis 7** — Celery broker, login-throttle store, and cross-process
  pub/sub bridge.
- **Python 3.12+** — backend API and Celery worker.
- **Node 20+** — frontend build (the runtime serves the built static assets).
- **A reverse proxy / load balancer** — to terminate TLS and route the API,
  WebSocket, and static frontend (required for any non-local deployment).
- **Object storage or a file path** — only if you choose to persist exported
  reports (reports are generated on demand and are not stored by default).

## Recommended demonstration architecture

A clearly labeled recommendation for a small, single-region demonstration
deployment. This is a starting point, not a production architecture.

```
                        ┌─────────────────────────────┐
   Internet ── TLS ───▶ │  Reverse proxy / load bal.  │
                        │  (HTTPS + WSS termination)  │
                        └───────┬───────────────┬─────┘
                                │               │
                     ┌──────────▼──────┐  ┌─────▼─────────────┐
                     │  Frontend (SPA) │  │  Backend API (xN)  │
                     │  static assets  │  │  FastAPI + WS      │
                     └─────────────────┘  └─────┬───────┬──────┘
                                                │       │
                              ┌─────────────────┘       └────────────────┐
                     ┌────────▼────────┐                  ┌───────────────▼──┐
                     │  PostgreSQL 16  │                  │     Redis 7      │
                     │  (state)        │                  │ broker + pub/sub │
                     └─────────────────┘                  └────────┬─────────┘
                                                                   │
                                                          ┌─────────▼────────┐
                                                          │ Celery worker(s) │
                                                          └──────────────────┘
```

- **Frontend** — build the Vite app and serve the static assets (or run the
  provided `frontend/Dockerfile`).
- **Backend API** — one or more stateless FastAPI replicas behind the proxy;
  each runs its own Redis bridge.
- **PostgreSQL** — a managed or self-hosted Postgres 16 instance.
- **Redis** — a managed or self-hosted Redis 7 instance.
- **Celery worker** — one or more workers consuming from the Redis broker.
- **Mock webhook** — optional in a demo; replace with a real integration
  target if you need real playbook side effects.
- **Metrics / tracing** — point the API at a Prometheus scraper and an OTLP
  collector if you want to consume the built-in observability.

## Environment variables

All configuration is environment-driven. See the full reference in the README
→ [Environment-variable reference](../README.md#environment-variable-reference)
and `.env.example`. For a non-local deployment you **must** set, at minimum:

- `ENVIRONMENT=production`
- `SECRET_KEY` — a strong, unique value (e.g. `openssl rand -hex 32`). The app
  **refuses to start** in production with the insecure default.
- `DATABASE_URL` — the Postgres DSN.
- `REDIS_URL` — the Redis URL.
- `CORS_ORIGINS` — the public frontend origin(s).
- `OTEL_ENABLED` / `OTEL_EXPORTER_ENDPOINT` — if you want tracing.

**Do not commit real secrets.** Store them in your platform's secret manager
or environment, never in the repository.

## Security considerations

- **Terminate TLS** at the proxy and serve the API and frontend over
  HTTPS/WSS; enforce HSTS.
- **Use a strong, unique `SECRET_KEY`** (the production guard enforces this).
- **Restrict CORS** to the public frontend origin(s) only.
- **Run services as non-root** (the Dockerfiles already do this).
- **Add general API rate limiting** and request-size limits (only login is
  throttled today).
- **Add SSO (OIDC) and MFA** before exposing the app to real users (not
  present today).
- **Keep the mock webhook out of production** or replace it with a real,
  authenticated integration target.
- **Ship structured logs and traces** to a central store.
- **Add a secret-scanning gate** (e.g. `gitleaks` / `trufflehog`) to CI.

See [`security.md`](security.md) for the full threat model and known gaps.

## Cost considerations

Costs depend entirely on the provider and scale you choose; the figures below
are **qualitative**, not quotes.

- **Small demonstration** (single region, low traffic): a modest monthly cost
  — a small Postgres, a small Redis, a couple of small API/worker instances,
  and a proxy. Often in the low tens of dollars per month on most cloud
  providers.
- **Growth** (more API/worker replicas, larger Postgres/Redis, a real
  message queue): cost rises with the number of replicas and the size of the
  data stores.
- **Avoid surprises** by setting budget alerts and by right-sizing after you
  have real traffic, not before.

Verify current pricing with your chosen provider before committing to a
budget.

## Deployment validation checklist

Before declaring a deployment healthy:

- [ ] `/health` returns 200 (liveness).
- [ ] `/ready` returns 200 (Postgres + Redis reachable).
- [ ] `/metrics` returns Prometheus metrics.
- [ ] The frontend loads and you can sign in with a known account.
- [ ] A WebSocket connection to an incident room succeeds and receives a
      `connected` event.
- [ ] A playbook run dispatches, executes in the worker, and reports
      `succeeded`.
- [ ] Cross-organization access is rejected (404/403).
- [ ] TLS is enforced and HSTS is present.
- [ ] No secrets appear in logs, responses, or the audit trail.
- [ ] The production guard accepted the configured `SECRET_KEY`.

## Rollback checklist

If a deployment must be rolled back:

- [ ] Identify the last known-good release / image tag.
- [ ] Point the proxy / load balancer back to the known-good release.
- [ ] Verify `/health` and `/ready` on the rolled-back version.
- [ ] Confirm the database schema is compatible (Alembic migrations are
      forward-only; coordinate any schema changes with the rollback).
- [ ] Verify the frontend and API versions are matched.
- [ ] Monitor logs and metrics for regressions after the rollback.
- [ ] Record the reason for the rollback and the time it took.

## Suggested future CI/CD workflow

The existing CI workflow already builds and tests. A reasonable future
deployment pipeline (not currently implemented) would be:

1. **On merge to the main branch:** run the existing CI (lint, types, tests,
   build, migration consistency, dependency scan).
2. **Build and push** the backend, frontend, and mock-webhook images to a
   registry, tagged with the commit SHA.
3. **Deploy to a staging environment** and run the deployment validation
   checklist above.
4. **Promote to production** after staging validation, using the rollback
   checklist if anything fails.
5. **Add a secret-scanning step** and **image vulnerability scanning** to the
   pipeline.

This is a recommendation for a future path; it is not configured in this
repository.
