# Demo Script

A guided walkthrough of the OpsCommand 9-step incident workflow. This mirrors
the end-to-end test in `frontend/e2e/incident-workflow.spec.ts` and is a good
script for a live demo.

## Preconditions

- Full stack running (see README → Local setup or Docker setup).
- Seeded: `python -m app.seed`.
- Worker running (required for step 7).
- Browser at <http://localhost:5173>.

**Sign in as:** `responder@acme-ops.io` / `Demo-Password-123!`
(Use `owner@acme-ops.io` to also demonstrate admin-only actions.)

---

## Step 1 — Sign in

1. Open <http://localhost:5173>.
2. Enter the responder email and password.
3. Observe the **connection indicator** (top bar) turn green once the
   WebSocket to the API is established.

> Talking point: auth is JWT-based with a short-lived access token and a
> rotating refresh token; the UI refreshes transparently on 401.

## Step 2 — Review the dashboard

1. The **Dashboard** shows active incidents, severity, and status.
2. Note the seeded active incident **Checkout latency spike** (SEV2).

> Talking point: the dashboard is a live, org-scoped view; data is fetched via
> the REST API and kept fresh by TanStack Query.

## Step 3 — Declare a new incident

1. Click **+ Declare incident**.
2. Fill in:
   - **Title:** `Payment gateway timeouts`
   - **Summary:** `Elevated 5xx on /pay since 15:20 UTC.`
   - **Severity:** `SEV1`
   - **Services:** check `checkout-api` and `orders-database`.
3. Click **Create**.

> Talking point: creation is authorized (requires `responder`+), validated,
> and immediately published to the incident room over WebSocket.

## Step 4 — Open the command view

1. Click the new incident to open **IncidentDetail**.
2. Observe the live sections: **Status**, **Roles**, **Timeline**,
   **Action items**, and **Playbooks**.

> Talking point: this is the single pane of glass for the incident.

## Step 5 — Transition status

1. In the **Status** card, click the transition button (e.g.
   `declared → investigating`).
2. Watch the **Timeline** update in real time with the status change.

> Talking point: transitions follow a validated state machine and use
> optimistic concurrency (`expected_version`) so two responders can't clobber
> each other.

## Step 6 — Assign roles

1. In the **Roles** card, assign:
   - `commander` → a user
   - `operations` → a user
2. Observe the assignments appear and the timeline event.

> Talking point: incident roles (commander, communications, operations,
> scribe) make ownership explicit during the incident.

## Step 7 — Run a playbook (real-time progress)

1. In the **Playbooks** card, select **Standard escalation**.
2. Click **Run Playbook**.
3. Watch the run status advance: `pending → running → succeeded`, with
   per-step progress streaming in live.

> Talking point: the playbook runs in a **background Celery worker**, is
> **idempotent** (safe to retry), **retries** transient failures, and streams
> progress to the browser via the **Redis pub/sub bridge** — even though the
> worker is a separate process.

## Step 8 — Add a timeline note

1. In the **Timeline** card, type a note (e.g. `Rolled back deploy 1234.`).
2. Click **Add**.
3. Observe it appear instantly for all connected viewers.

> Talking point: the timeline is an append-only, auditable record of the
> incident.

## Step 9 — Export the report

1. Click **Export Report**.
2. A Markdown file `incident-<id>-report.md` downloads, summarizing the
   incident, its timeline, roles, and action items.

> Talking point: reports are generated on demand from the same source of
> truth, so they always reflect the current state.

---

## Bonus: demonstrate authorization

1. Sign out and sign in as `viewer@acme-ops.io`.
2. Observe that write actions (declare, transition, run playbook) are
   disabled / rejected — the viewer is read-only.
3. Sign in as a user from a *different* organization (if seeded) and observe
   that the other org's incidents are not accessible (403/404).

> Talking point: authorization is enforced server-side on every route; the UI
> is never the security boundary.
