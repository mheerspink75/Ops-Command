# OpsCommand Portfolio Audit

This audit evaluates the OpsCommand repository as a portfolio piece from four
perspectives — a non-technical recruiter, an engineering hiring manager, a
senior software engineer, and an operations/SRE interviewer — and records the
presentation and evidence gaps that this improvement pass addresses.

All observations below are based on a direct inspection of the checked-out
repository (branch `feature/initial-opscommand-platform`, HEAD
`cff3d28`). Nothing here is inferred from marketing copy; each claim is tied
to a file, a test, or a command result.

## Executive Summary

OpsCommand is a genuinely strong full-stack reference implementation. The
engineering substance is real and verifiable: a layered FastAPI backend with
server-side, organization-scoped authorization; a durable Celery playbook
executor with idempotency and retries; a cross-process real-time bridge over
Redis pub/sub; optimistic concurrency on incident mutations; and a React +
TypeScript frontend with a typed API client and WebSocket hook. The
repository ships a CI workflow, six architecture decision records, and a
three-level test pyramid (backend pytest, frontend Vitest, Playwright e2e).

The gap is **presentation, not substance**. A recruiter opening the
repository today sees a thorough but dense README that leads with
implementation detail rather than the business problem, has no visual proof,
no live-demo path, and no reusable resume/interview content. The project's
value is real but buried. This pass reorders the README to lead with the
problem and value, adds a screenshot capture plan, a recruiter-focused demo
script and video checklist, deployment guidance, resume/interview content, a
portfolio showcase, and a transparent before/after impact review — without
removing any of the existing technical depth.

## Current Strengths

- **Real, layered architecture.** Routes → services → models with a strict
  dependency direction (`docs/architecture.md`, `backend/app/`). Business
  rules live in `services/`, not in route handlers.
- **Server-side, organization-scoped authorization.** Every org-scoped route
  resolves membership and role; cross-org access returns 404/403
  (`backend/app/security/auth.py`, ADR-001). The frontend is explicitly not a
  security boundary.
- **Durable background execution.** Playbook runs are keyed by an
  `idempotency_key`, retry transient failures, and stream progress to the
  browser across processes via a Redis pub/sub bridge (ADR-002, ADR-003,
  `backend/app/worker/tasks.py`).
- **Concurrency correctness.** Optimistic concurrency via `Incident.version`
  + `expected_version` prevents lost updates (ADR-004); a validated state
  machine governs status transitions.
- **Strong tenancy and auth.** Argon2id password hashing, short-lived JWT
  access tokens with rotating, revocable refresh tokens, and Redis-backed
  login throttling (ADR-005, `backend/app/security/`).
- **Reproducible local stack.** A deterministic `mock-webhook` service means
  playbooks and tests never depend on a paid external API (ADR-006).
  `docker-compose.yml` brings up the whole stack.
- **Serious quality gates.** A CI workflow runs backend lint/type/test,
  frontend lint/type/test/build, migration consistency, Docker image builds,
  and dependency scanning (`.github/workflows/ci.yml`).
- **Decision documentation.** Six ADRs capture the "why" behind the
  significant choices (`docs/decisions/`).
- **Verified in this environment.** Backend Ruff + mypy pass; frontend
  ESLint + `tsc` + Vitest (63 tests) + production build all pass.

## Recruiter Perspective

What a non-technical recruiter sees first is the README opening. Today it
opens with a correct but dense technical description ("self-contained
incident-response command platform … FastAPI + SQLAlchemy + Celery …"). A
recruiter scanning for 20 seconds will not extract:

- **What problem it solves** (coordinating an incident response).
- **Who it is for** (small engineering / on-call teams).
- **Why it matters** (faster, calmer, more accountable incident response).
- **What it looks like** (no screenshots, no demo video, no live link).

The word "incident" appears, but the business value — reducing time-to-
resolve, making ownership explicit, producing an auditable record — is not
stated up front. There is also no resume-ready summary a recruiter can lift.

**Verdict:** The project is clearly a real, non-trivial build, but the
recruiter cannot quickly tell *why* it matters or *see* it working.

## Hiring Manager Perspective

A hiring manager will look for evidence of senior judgment. The repository
delivers it, but it is spread across `docs/` and the ADRs rather than
surfaced:

- **Good:** the ADRs show trade-off reasoning (e.g. why real-time is an
  optimization, not a correctness dependency; why idempotency is required).
  The "Known limitations" section is honest and specific, which reads as
  senior.
- **Gap:** the README does not connect the architecture to the business
  outcome. A hiring manager wants to see "we chose X because it serves Y,"
  and that mapping is implicit rather than explicit.
- **Gap:** there is no single place that says "here is what I would show you
  in a 90-second demo," which is exactly what a hiring manager asks for.

**Verdict:** Strong signals of senior engineering, but the candidate has to
dig for them. A tighter narrative would make the case faster.

## Senior Engineer Perspective

A senior engineer will read the code and the ADRs and find the design sound:

- Clean separation of concerns; thin routes; transaction boundaries in
  services; real-time publishing after commit.
- Correct handling of the hard parts: cross-process event delivery,
  idempotent retries, optimistic concurrency, token rotation.
- Honest limitations (at-most-once real-time, no general rate limiting, no
  SSO/MFA).

**Gap:** the README's "Verified results" line ("backend 96/96 … frontend
63/63 … e2e 2/2") is a point-in-time claim. In this environment the backend
pytest suite and the Playwright e2e suite could not be executed (they require
Postgres/Redis and a running stack). A senior reviewer will want the
*reproducible command* and the *conditions* under which the result holds, not
just a number. This pass keeps the numbers but anchors them to the exact
commands and states the environment dependency.

## Operations and SRE Perspective

An SRE interviewer will look for operational maturity:

- **Good:** structured logging (structlog), Prometheus `/metrics`, optional
  OpenTelemetry tracing, request-ID propagation, `/health` + `/ready`
  probes, and a production guard that refuses to boot with the insecure
  default secret.
- **Good:** the mock webhook and the deterministic seed data make the system
  observable and reproducible in a demo.
- **Gap:** there is no deployment guidance — no "how would this run in a
  real environment," no cost/security considerations, no CI/CD path beyond
  the existing test workflow. This pass adds `docs/deployment-options.md`
  that is clearly labeled as a future/optional path (no live deployment is
  claimed).

## Presentation Gaps

1. **No visual proof.** The README references screenshot files that do not
   exist. There is no demo video and no live URL.
2. **README leads with implementation.** Business value and the "who/why"
   are not in the first screen.
3. **No 20-second story.** A recruiter cannot state what the project does and
   why it matters without reading the whole README.
4. **No demo script for a live walkthrough.** `docs/demo-script.md` exists
   and is good, but it is framed as a test mirror, not a recruiter-facing
   narrative with talking points per audience.
5. **No video checklist.** Nothing guides recording a shareable demo.
6. **No deployment guidance.** No "how to run this beyond a laptop" path.
7. **No resume/interview content.** No reusable bullets, STAR examples, or
   talking points.
8. **No portfolio showcase.** No single case-study document reusable across
   a portfolio site, LinkedIn, and applications.
9. **No before/after impact framing.** No transparent rubric showing what
   improved and why.

## Evidence Gaps

- **Test counts are point-in-time.** The backend (96) and e2e (2) results
  cannot be reproduced in an environment without Postgres/Redis and a running
  stack. They should be presented as "verified in the documented
  development environment," with the exact commands, not as a standing
  guarantee.
- **No coverage numbers.** No coverage tooling or thresholds are configured;
  none should be claimed.
- **No live deployment.** No public URL exists; none should be claimed.
- **No screenshots.** No authentic captures exist; placeholders must stay
  clearly labeled and a capture plan must be provided.
- **No performance data.** No load or latency results exist; none should be
  claimed.

## Recommended Improvements

1. **Reorder the README** to lead with the problem, value, capabilities, and
   a 20-second story; keep all technical depth below.
2. **Add a screenshot capture plan** (`docs/screenshots/README.md`) with
   exact steps per screen, and keep placeholders clearly labeled.
3. **Elevate the demo script** into a recruiter-facing narrative with
   per-audience talking points, plus a **video checklist**.
4. **Add deployment guidance** clearly labeled as a future/optional path.
5. **Add resume/interview content** with verified-only bullets and STAR
   examples.
6. **Add a portfolio showcase** case study reusable across surfaces.
7. **Add a transparent recruiter-impact review** with a stated rubric.
8. **Anchor every quality claim** to a reproducible command and state the
   environment conditions.

## Priority Matrix

Priority reflects impact on the 20-second recruiter read and on interview
readiness, weighted by how much each gap currently undermines the project's
real strengths.

| Priority | Item | Why this priority |
|----------|------|-------------------|
| **Critical** | README leads with business value + 20-second story | This is the first thing a recruiter sees; it currently leads with implementation. |
| **Critical** | No fake screenshots / no fake live demo | Claiming assets that don't exist would undermine credibility; must be handled honestly. |
| **High** | Screenshot capture plan + labeled placeholders | Visual proof is the single biggest missing recruiter signal; a plan makes it actionable. |
| **High** | Recruiter-facing demo script + video checklist | Demonstrability is a top interview ask; the content exists but is not framed for the audience. |
| **High** | Resume/interview content | Directly reusable; high leverage for applications and interviews. |
| **Medium** | Deployment guidance (labeled future/optional) | Shows operational thinking; must not imply a live deployment. |
| **Medium** | Portfolio showcase case study | Reusable across portfolio/LinkedIn/applications. |
| **Medium** | Transparent recruiter-impact review | Documents the improvement and its rationale. |
| **Low** | Anchor quality claims to reproducible commands | Important for credibility; the underlying checks already pass. |
