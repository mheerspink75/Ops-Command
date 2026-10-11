# OpsCommand Demo Script

A guided, recruiter-facing walkthrough of the OpsCommand incident workflow.
It mirrors the end-to-end test in `frontend/e2e/incident-workflow.spec.ts`, so
what you demo is exactly what the automated test exercises. Use the
**60-second** or **90-second** version depending on the audience, and lean on
the per-audience talking points to land the right message.

## Target audience

- **Recruiters / hiring coordinators** — need to understand what the project
  is and why it matters in under a minute.
- **Engineering hiring managers** — want to see senior judgment and a clear
  problem/solution story.
- **Senior engineers / interviewers** — want to see the hard parts done
  correctly (real-time, concurrency, durable background work, tenancy).
- **Operations / SRE interviewers** — want to see operational maturity
  (observability, audit, runbooks).

## Demo goal

Show, in 60–90 seconds, that OpsCommand gives a team **one calm, live,
auditable place to run an incident**: declare it, see who is in charge and
what is affected, take repeatable actions, watch it update in real time, and
produce a post-incident report. The goal is to make the *value* obvious, then
let the *engineering* speak for itself.

## Prerequisites

- Full stack running (see README → [Quick start](../README.md#quick-start) or
  [Docker setup](../README.md#docker-setup)).
- Seeded: `docker compose exec backend python -m app.seed` (or `make seed`).
- Worker running (required for the playbook step) — the `worker` service in
  Compose.
- Browser at <http://localhost:5173> in a clean profile.
- A second browser tab/window available (for the real-time scene).

**Sign in as:** `responder@acme-ops.io` / `Demo-Password-123!`
(Use `owner@acme-ops.io` to also demonstrate admin-only actions.)

## Demo data

The seed command creates a demo organization (**Acme Operations**) with:

- One user per role (owner, administrator, responder, viewer), all sharing the
  non-production password `Demo-Password-123!`.
- Four services: `checkout-api` (critical), `orders-database` (critical),
  `session-cache` (standard), `event-queue` (standard), with dependencies.
- An **active** incident: **Checkout latency spike** (SEV2, investigating).
- A **resolved** incident: **Cache eviction storm** (SEV3).
- A sample playbook: **Standard escalation** (timeline, action item, status
  change, wait, snapshot steps).

These are the states the demo relies on. If a scene looks empty, re-run the
seed command.

## 60-second version

A tight pass for a recruiter or a first impression. One idea per beat:

1. **(5s)** Open the app, sign in. "This is a live incident command view."
2. **(10s)** Dashboard: point at the active SEV2 incident. "One shared, live
   view of what's on fire."
3. **(15s)** Open the incident: status, roles, affected services, timeline.
   "Who's in charge, what's affected, what we've tried."
4. **(15s)** Run the **Standard escalation** playbook; watch per-step progress
   stream in. "Repeatable actions, running in the background, updating live."
5. **(10s)** Switch tabs to show the same change appear without a reload.
   "Real-time, across processes."
6. **(5s)** Export the report. "And it produces an accountable record."

## 90-second version

The full story, with the authorization and concurrency beats added:

1. **Sign in** (5s) — note the connection indicator turn green.
2. **Dashboard** (10s) — active incident, severity, status.
3. **Open the command view** (15s) — status, roles, timeline, action items,
   playbooks.
4. **Transition status** (10s) — `declared → investigating`; watch the
   timeline update.
5. **Assign roles** (10s) — commander + operations; ownership becomes
   explicit.
6. **Run a playbook** (15s) — watch `pending → running → succeeded` with
   per-step progress.
7. **Real-time proof** (10s) — a second tab shows the change live.
8. **Resolve + report** (10s) — advance to resolved, export the Markdown
   report.
9. **Authorization beat** (5s) — sign in as `viewer` and show write actions
   are disabled.

## Narration script

The step-by-step walkthrough. Each step lists what to do and a one-line
talking point. This is the detailed version of the 60/90-second beats above.

### Step 1 — Sign in

1. Open <http://localhost:5173>.
2. Enter the responder email and password.
3. Observe the **connection indicator** (top bar) turn green once the
   WebSocket to the API is established.

> Talking point: auth is JWT-based with a short-lived access token and a
> rotating refresh token; the UI refreshes transparently on 401.

### Step 2 — Review the dashboard

1. The **Dashboard** shows active incidents, severity, and status.
2. Note the seeded active incident **Checkout latency spike** (SEV2).

> Talking point: the dashboard is a live, org-scoped view; data is fetched via
> the REST API and kept fresh by TanStack Query.

### Step 3 — Open the command view

1. Click the active incident to open **IncidentDetail**.
2. Observe the live sections: **Status**, **Roles**, **Timeline**,
   **Action items**, and **Playbooks**.

> Talking point: this is the single pane of glass for the incident.

### Step 4 — Transition status

1. In the **Status** card, click the transition button (e.g.
   `declared → investigating`).
2. Watch the **Timeline** update in real time with the status change.

> Talking point: transitions follow a validated state machine and use
> optimistic concurrency (`expected_version`) so two responders can't clobber
> each other.

### Step 5 — Assign roles

1. In the **Roles** card, assign:
   - `commander` → a user
   - `operations` → a user
2. Observe the assignments appear and the timeline event.

> Talking point: incident roles (commander, communications, operations,
> scribe) make ownership explicit during the incident.

### Step 6 — Run a playbook (real-time progress)

1. In the **Playbooks** card, select **Standard escalation**.
2. Click **Run Playbook**.
3. Watch the run status advance: `pending → running → succeeded`, with
   per-step progress streaming in live.

> Talking point: the playbook runs in a **background Celery worker**, is
> **idempotent** (safe to retry), **retries** transient failures, and streams
> progress to the browser via the **Redis pub/sub bridge** — even though the
> worker is a separate process.

### Step 7 — Add a timeline note

1. In the **Timeline** card, type a note (e.g. `Rolled back deploy 1234.`).
2. Click **Add**.
3. Observe it appear instantly for all connected viewers.

> Talking point: the timeline is an append-only, auditable record of the
> incident.

### Step 8 — Resolve and export the report

1. Advance the status to **resolved** (or use the seeded resolved incident).
2. Click **Export Report**.
3. A Markdown file `incident-<id>-report.md` downloads, summarizing the
   incident, its timeline, roles, and action items.

> Talking point: reports are generated on demand from the same source of
> truth, so they always reflect the current state.

### Bonus — demonstrate authorization

1. Sign out and sign in as `viewer@acme-ops.io`.
2. Observe that write actions (declare, transition, run playbook) are
   disabled / rejected — the viewer is read-only.
3. Sign in as a user from a *different* organization (if seeded) and observe
   that the other org's incidents are not accessible (403/404).

> Talking point: authorization is enforced server-side on every route; the UI
> is never the security boundary.

## Recruiter talking points

- "This is the kind of software teams use to run production incidents — the
  same category as PagerDuty, incident.io, FireHydrant, and Opsgenie (category
  comparison only, not an affiliation)."
- "The whole point is one calm, shared, live view so a team stops coordinating
  in chat threads."
- "It's a complete, working full-stack app — not a mockup — and it runs
  locally with no paid services."
- "There's a test suite, CI, and architecture decision records, which shows
  how it was built, not just that it works."

## Hiring manager talking points

- "I framed the problem first (incident coordination under pressure) and then
  built to it — the architecture serves the business outcome."
- "The hard parts are handled deliberately: cross-process real-time, durable
  idempotent background work, optimistic concurrency, and strict tenancy.
  Each has an ADR explaining the trade-off."
- "I kept the system honest about its limits — at-most-once real-time, no SSO
  yet — rather than overclaiming."
- "It's reproducible: one command brings up the whole stack, and the demo is
  exactly what the end-to-end test exercises."

## Technical interview talking points

- **Real-time across processes:** the `RealtimeHub` delivers in-process and
  publishes to Redis; a bridge thread in the API process subscribes and
  forwards to WebSocket clients, so a worker's progress reaches the browser.
- **Durable background work:** playbook runs are keyed by an
  `idempotency_key`, retry transient failures with backoff, and re-check
  terminal status before doing work.
- **Concurrency:** `Incident.version` + `expected_version` gives optimistic
  concurrency; a validated state machine governs transitions.
- **Tenancy:** every org-scoped route resolves membership and role; unknown
  orgs return 404, non-members 403.
- **Auth:** Argon2id hashing, short-lived JWT access tokens, rotating
  revocable refresh tokens, Redis-backed login throttling.

## Recovery steps

If something goes wrong mid-demo:

- **Blank / empty dashboard:** re-run the seed command
  (`docker compose exec backend python -m app.seed`) and reload.
- **Playbook stuck at `pending`:** confirm the `worker` service is running
  (`docker compose ps`); on Windows, the worker may need `--pool=solo`.
- **No real-time updates:** check the connection indicator; confirm the
  WebSocket URL (`VITE_WS_URL`) points at the API.
- **Login fails:** confirm the demo password `Demo-Password-123!` and that
  the user is a member of the seeded org.
- **API not responding:** check `docker compose ps` and the backend health
  endpoint (`/health`).
- **If a step truly cannot be recovered:** fall back to the seeded resolved
  incident and the report export, and narrate the rest from the UI.

## Final call to action

- "The full source, tests, and architecture decision records are in the
  repository — happy to walk through any part of it."
- "I can also show the end-to-end test that drives this exact workflow, or
  the ADRs that explain the trade-offs behind the design."
- "If you'd like, I can point you at the deployment options and how this
  would run beyond a laptop."
