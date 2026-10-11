# OpsCommand Screenshot Capture Plan

This is a **capture plan**, not a set of finished images. No screenshots are
included in this repository yet because authentic captures could not be taken
in the environment where this work was done (no browser / display tooling was
available). Rather than ship placeholder or fabricated images, this document
gives exact, repeatable steps to produce real captures of the **current**
frontend, and where each one should go.

**Rules for every capture**

- Capture only real application states from the running app. Do not mock up,
  hand-draw, or reuse stock images.
- Use the seeded demo data (see [Seed data](../../README.md#seed-data)) so the
  captures are reproducible.
- Do **not** show secrets, tokens, browser extensions, personal desktop
  content, or unrelated windows.
- Crop consistently to the application viewport (no browser chrome unless a
  specific scene calls for it).
- Save as **PNG** (or WebP if a repository convention is adopted later) at the
  recommended dimensions below.
- Verify each image opens correctly and matches the described state before
  committing it.
- Give each image a descriptive `alt` (provided below) for accessibility.

**How to get the app into a capturable state**

1. Start the full stack: `cp .env.example .env && docker compose up --build`.
2. Seed demo data: `docker compose exec backend python -m app.seed` (or
   `make seed`).
3. Start the worker (required for playbook progress): it runs as the
   `worker` service in Compose.
4. Open <http://localhost:5173> in a clean browser profile.
5. Sign in as `responder@acme-ops.io` / `Demo-Password-123!` (use
   `owner@acme-ops.io` for admin-only scenes).

---

## 1. Login screen

- **Filename:** `login.png`
- **Route / page:** `/login`
- **Required demo state:** Signed out; the sign-in form is visible.
- **Exact capture steps:**
  1. Open <http://localhost:5173/login> in a clean profile.
  2. Optionally type the responder email into the email field (leave the
     password field empty or masked).
  3. Capture the viewport.
- **Content that must appear:** the OpsCommand name/branding, the email and
  password fields, and the sign-in button.
- **Content that must not appear:** any real password value, tokens, or
  personal data.
- **Recommended dimensions:** 1280×800 px
- **Recommended aspect ratio:** 16:10
- **Suggested alt text:** "OpsCommand sign-in screen with email and password
  fields."
- **Recommended README placement:** [Demo preview](../../README.md#demo-preview)
  section, first image.
- **Why it matters to recruiters:** shows the product has a real, polished
  entry point and a professional look.
- **Why it matters to interviewers:** a clean auth entry point is the first
  thing a reviewer sees; it sets the tone for the rest of the UI.

## 2. Incident dashboard

- **Filename:** `dashboard.png`
- **Route / page:** `/` (Dashboard)
- **Required demo state:** Signed in as a responder; the seeded active
  incident **Checkout latency spike** (SEV2, investigating) is visible.
- **Exact capture steps:**
  1. Sign in as `responder@acme-ops.io`.
  2. Land on the Dashboard.
  3. Confirm the active incident row and the connection indicator are visible.
  4. Capture the viewport.
- **Content that must appear:** the organization name, the active incident
  with its severity and status, and the live connection indicator.
- **Content that must not appear:** other organizations' data, secrets, or
  personal data.
- **Recommended dimensions:** 1440×900 px
- **Recommended aspect ratio:** 16:10
- **Suggested alt text:** "OpsCommand dashboard showing an active SEV2
  incident and a live connection indicator."
- **Recommended README placement:** [Demo preview](../../README.md#demo-preview)
  section, second image.
- **Why it matters to recruiters:** the "at a glance" view that communicates
  the core value (one shared, live view of incidents).
- **Why it matters to interviewers:** demonstrates the org-scoped, live data
  model and the real-time connection state.

## 3. Incident detail (command view)

- **Filename:** `incident-detail.png`
- **Route / page:** `/incidents/:incidentId` (IncidentDetail)
- **Required demo state:** The active incident is open, showing status,
  roles, timeline, action items, and playbooks.
- **Exact capture steps:**
  1. From the Dashboard, open the **Checkout latency spike** incident.
  2. Let the page fully load (status, roles, timeline, action items,
     playbooks).
  3. Capture the viewport.
- **Content that must appear:** the incident title, severity, status, the
  affected services, the roles card, the timeline, and the playbooks card.
- **Content that must not appear:** secrets, tokens, or other orgs' data.
- **Recommended dimensions:** 1440×900 px
- **Recommended aspect ratio:** 16:10
- **Suggested alt text:** "OpsCommand incident command view showing status,
  roles, timeline, action items, and playbooks."
- **Recommended README placement:** [Demo preview](../../README.md#demo-preview)
  section, third image.
- **Why it matters to recruiters:** the "single pane of glass" that is the
  heart of the product.
- **Why it matters to interviewers:** shows the full incident model and the
  real-time command surface in one view.

## 4. Incident timeline

- **Filename:** `incident-timeline.png`
- **Route / page:** `/incidents/:incidentId` (the Timeline card)
- **Required demo state:** The timeline shows the seeded events (declared,
  status change) plus one newly added note.
- **Exact capture steps:**
  1. Open the active incident.
  2. In the Timeline card, add a note (e.g. `Rolled back deploy 1234.`).
  3. Confirm the new entry appears.
  4. Capture the Timeline card (or the viewport).
- **Content that must appear:** the ordered, append-only event list with the
  new note at the bottom.
- **Content that must not appear:** secrets or personal data.
- **Recommended dimensions:** 1280×800 px
- **Recommended aspect ratio:** 16:10
- **Suggested alt text:** "OpsCommand incident timeline showing an
  append-only, auditable event log."
- **Recommended README placement:** [Demo preview](../../README.md#demo-preview)
  section, fourth image.
- **Why it matters to recruiters:** shows the accountable, auditable record
  that supports post-incident review.
- **Why it matters to interviewers:** demonstrates the append-only event log
  and the real-time append behavior.

## 5. Real-time update activity

- **Filename:** `realtime-activity.png`
- **Route / page:** `/incidents/:incidentId` with a second browser tab open
- **Required demo state:** Two tabs on the same incident; an action in one
  tab (e.g. a status change or timeline note) is reflected live in the other.
- **Exact capture steps:**
  1. Open the incident in two browser tabs (or two windows).
  2. In tab A, make a change (add a timeline note or transition status).
  3. In tab B, capture the moment the change appears without a manual reload.
- **Content that must appear:** the same incident in both tabs, with the new
  event visible in the "passive" tab.
- **Content that must not appear:** secrets, tokens, or personal data.
- **Recommended dimensions:** 1600×1000 px (side-by-side) or 1440×900 px
  (single tab)
- **Recommended aspect ratio:** 16:10
- **Suggested alt text:** "OpsCommand real-time update: a change made in one
  tab appears live in another."
- **Recommended README placement:** [Demo preview](../../README.md#demo-preview)
  section, fifth image.
- **Why it matters to recruiters:** the "live" feel is a strong, visible
  differentiator.
- **Why it matters to interviewers:** this is the clearest visual proof of
  the WebSocket + Redis pub/sub bridge working across processes.

## 6. Playbook execution progress

- **Filename:** `playbook-run.png`
- **Route / page:** `/incidents/:incidentId` (the Playbooks card)
- **Required demo state:** A playbook run is in progress or just completed,
  showing per-step progress.
- **Exact capture steps:**
  1. Open the active incident.
  2. In the Playbooks card, select **Standard escalation** and click
     **Run Playbook**.
  3. Capture the run as it advances (`pending → running → succeeded`) with
     per-step progress visible.
- **Content that must appear:** the selected playbook, the run status, and
     the per-step progress list.
- **Content that must not appear:** secrets, tokens, or webhook payloads that
     contain sensitive data.
- **Recommended dimensions:** 1440×900 px
- **Recommended aspect ratio:** 16:10
- **Suggested alt text:** "OpsCommand playbook execution showing live,
  per-step progress."
- **Recommended README placement:** [Demo preview](../../README.md#demo-preview)
  section, sixth image.
- **Why it matters to recruiters:** shows automation of the "what do we do
  next" steps.
- **Why it matters to interviewers:** the strongest visual proof of durable,
  idempotent background execution with real-time progress.

## 7. Metrics / observability view

- **Filename:** `metrics.png`
- **Route / page:** `/metrics` (Metrics page)
- **Required demo state:** The Metrics page is showing metric groups with
  values (from the backend `/metrics` endpoint).
- **Exact capture steps:**
  1. Sign in and navigate to `/metrics`.
  2. Let the metric groups load.
  3. Capture the viewport.
- **Content that must appear:** the metric groups and their values.
- **Content that must not appear:** secrets, tokens, or internal hostnames
  that are not meant to be public.
- **Recommended dimensions:** 1440×900 px
- **Recommended aspect ratio:** 16:10
- **Suggested alt text:** "OpsCommand metrics view showing observability
  metric groups."
- **Recommended README placement:** [Demo preview](../../README.md#demo-preview)
  section, seventh image.
- **Why it matters to recruiters:** signals operational maturity.
- **Why it matters to interviewers:** shows the Prometheus metrics surface and
  the observability story.

## 8. Post-incident report workflow

- **Filename:** `post-incident-report.png`
- **Route / page:** `/incidents/:incidentId` (the Export Report action) and
  the downloaded Markdown
- **Required demo state:** The incident is resolved; the report has been
  generated and is visible (either the download prompt or the rendered
  Markdown).
- **Exact capture steps:**
  1. Open a resolved incident (e.g. **Cache eviction storm**).
  2. Click **Export Report**.
  3. Capture the download prompt, or open the downloaded
     `incident-<id>-report.md` and capture the rendered content.
- **Content that must appear:** the report summary (incident, timeline,
  roles, action items) or the download confirmation.
- **Content that must not appear:** secrets, tokens, or personal data.
- **Recommended dimensions:** 1280×800 px
- **Recommended aspect ratio:** 16:10
- **Suggested alt text:** "OpsCommand post-incident report generated from the
  incident's source of truth."
- **Recommended README placement:** [Demo preview](../../README.md#demo-preview)
  section, eighth image.
- **Why it matters to recruiters:** closes the loop — the incident produces a
  reusable, accountable artifact.
- **Why it matters to interviewers:** shows the report is generated on demand
  from the same source of truth, not a separate store.

---

## After capturing

1. Place each file in this directory (`docs/screenshots/`).
2. Update the [Demo preview](../../README.md#demo-preview) and
   [Screenshots](../../README.md#screenshots) sections of the README to embed
   the real images with the suggested alt text, replacing the "no screenshots
   yet" note.
3. Commit each image as its own individual commit (one file per commit).
4. Re-run the internal-link and image-path verification before pushing.
