# Testing

OpsCommand is tested at three levels: **backend** (pytest), **frontend unit**
(Vitest + React Testing Library), and **end-to-end** (Playwright). Linting and
type-checking are separate quality gates.

## Test pyramid

```
        /\
       /  \        E2E (Playwright) — few, high-value, full-stack
      / E2E\
     /------\
    /  Unit  \      Frontend unit (Vitest + RTL) — components & hooks
   /----------\
  /   Backend  \    Backend (pytest) — API, services, auth, worker
 /______________\
```

## Running the suites

All commands assume the infrastructure (Postgres + Redis) is running:

```bash
docker compose up -d postgres redis
```

### Backend

```bash
cd backend
python -m pytest -q                 # full suite
python -m pytest tests/test_auth.py # a single file
python -m pytest -k throttle        # by keyword
```

### Frontend unit

```bash
cd frontend
npm test -- --run                   # run once (CI mode)
npx vitest run src/pages/Login.test.tsx   # a single file
```

### End-to-end

```bash
cd frontend
npm run e2e                         # Playwright
```

E2E tests require the **full stack** running (API, worker, frontend) because
they exercise real HTTP + WebSocket + background execution. See
`frontend/e2e/global-setup.ts` for the preconditions.

### Lint & type-check

```bash
# Backend
cd backend
python -m ruff check .              # lint
python -m ruff format --check .     # format check
python -m mypy app                  # types

# Frontend
cd frontend
npm run lint                        # ESLint
npm run typecheck                   # tsc
npm run format:check                # Prettier
```

### Build

```bash
cd frontend
npm run build                       # production build (tsc -b && vite build)
```

## What is covered

### Backend (`backend/tests/`)

- **`test_auth.py`** — register, login, refresh rotation, logout, `/me`,
  login throttling, and cross-org authorization.
- **`test_incidents.py`** — create, list, get, update, status transitions
  (valid + invalid), role assignment, optimistic-concurrency conflicts, and
  org isolation.
- **`test_audit.py`** — audit log creation and payload sanitization.
- **`test_playbooks.py`** — playbook run dispatch, idempotency (duplicate key
  returns the same run), step execution, and retry behavior.
- **`test_reports.py`** — report generation and download.
- **`test_export.py`** — export endpoints.
- **`test_websocket.py`** — WebSocket authorization (authorized + rejected).
- **`test_worker.py`** — worker task execution and idempotency.
- **`test_health.py`** — health/readiness endpoints.

### Frontend unit (`frontend/src/**/*.test.*`)

- **Pages** — `Login`, `Dashboard`, `IncidentList`, `IncidentDetail`,
  `Metrics`.
- **Components** — `ConnectionIndicator`, `SeverityBadge`, `StatusBadge`.
- **Contexts** — `AuthContext`, `OrgContext`.
- **Hooks** — `useIncidentSocket`.
- **API client** — `client.ts` (request shaping, 401 handling, pagination).

### End-to-end (`frontend/e2e/`)

- **`incident-workflow.spec.ts`** — the full 9-step incident workflow:
  login → declare incident → set severity/services → transition status →
  assign roles → add timeline event → run playbook (and observe real-time
  progress) → export report. Plus a login-error case.

## Verified results

In the local development environment used for this build:

| Suite | Result |
|-------|--------|
| Backend (pytest) | 96 passed |
| Frontend unit (Vitest) | 63 passed |
| End-to-end (Playwright) | 2 passed |
| Backend lint (Ruff) | clean |
| Backend types (mypy) | clean |
| Frontend lint (ESLint) | clean |
| Frontend build | success |

These are point-in-time results from the local environment, not a CI-enforced
coverage threshold.

## Conventions

- **Backend tests** use a real Postgres (via the compose service) and a
  transactional fixture that rolls back per test, so the suite is isolated and
  repeatable.
- **Frontend unit tests** mock the API client and WebSocket to test component
  behavior in isolation.
- **E2E tests** are written against the real stack and are the primary guard
  against integration regressions (e.g. API/worker/frontend contract drift).
- Tests must **exercise real behavior** — a test that passes without touching
  the code path it claims to cover is a defect.
