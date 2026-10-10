# Security

This document describes the security model of OpsCommand and the threat
considerations it addresses. It is a reference implementation for a local
development stack; treat the guidance here as a baseline, not a hardened
production posture.

## Threat model (in scope)

- **Cross-organization data access** — a user in org A must not read or write
  org B's data, including via direct URL/ID guessing.
- **Privilege escalation** — a lower-privileged role must not perform
  higher-privileged actions.
- **Credential attacks** — brute-force login, password disclosure, token
  theft/reuse.
- **Secret leakage** — secrets must not appear in logs, audit records, error
  responses, or playbook failure details.
- **Denial of service** — unbounded login attempts.

## Authorization

Authorization is enforced **server-side on every route**. The frontend is
never a security boundary.

- **`get_current_user`** verifies the bearer access token (signature, expiry,
  `type == "access"`) and that the user exists and is active.
- **`get_org_context`** resolves the caller's membership in the target
  organization. It returns **404** for an unknown org and **403** for a
  non-member, so a caller cannot probe or access another org's resources by
  ID.
- **`require_role(min_role)`** enforces a minimum role using the hierarchy
  `viewer(1) < responder(2) < administrator(3) < owner(4)`.

Read endpoints require membership; write endpoints (create/update/transition/
assign/run) require at least `responder`.

## Authentication

- **Passwords** are hashed with **Argon2id** (`argon2-cffi`). Plaintext
  passwords are never stored or logged.
- **Access tokens** are short-lived JWTs (default 15 minutes) signed with
  `SECRET_KEY` (HS256). They carry `sub` (user id) and `type: "access"`.
- **Refresh tokens** are long-lived (default 14 days), stored server-side,
  **rotated** on each refresh, and **revocable** on logout. Rotation means a
  stolen refresh token is single-use.
- **Login throttling** is per-identifier and backed by Redis (default 5
  failed attempts per 60 s), raising a 429 when exceeded.

## Production guard

`main.py` refuses to start when `ENVIRONMENT=production` and the insecure
default `SECRET_KEY` is in use (controlled by `ENFORCE_SECURE_SECRET`). This
prevents the most common misconfiguration: shipping the dev secret to
production.

## Secrets handling

- All secrets are read from the environment (`.env` / orchestrator), never
  committed. `.env` is git-ignored; only `.env.example` (with placeholder
  values) is tracked.
- **Audit sanitization** (`core/sanitize.py`) redacts sensitive fields before
  they are written to the audit log.
- **Playbook failure details** are normalized and never include request
  bodies or credentials.
- The mock webhook echoes payloads for local debugging only; it is not a
  production integration.

## Transport & CORS

- **CORS** is restricted to the configured `CORS_ORIGINS`.
- In production, terminate TLS at a reverse proxy / load balancer and serve
  the API and frontend over HTTPS/WSS. The local stack uses plain HTTP/WS for
  convenience.

## WebSocket authorization

The incident WebSocket is authorized **at connect time** (before the socket is
accepted): the access token is verified and the caller's membership in the
incident's organization is checked. Unauthorized connections are closed with
code `4401`. This prevents a user from subscribing to another org's incident
room.

## Audit log

The audit log is organization-scoped and append-only. It records who did what
to which resource, with sanitized payloads, to support post-incident review.

## Known gaps (see README)

- No SSO / MFA / SCIM.
- No general API rate limiting (only login is throttled).
- Real-time delivery is at-most-once (Redis pub/sub), not a durable queue.
- No automated secret-scanning gate is configured in this repo yet (a CI
  workflow is provided; see `docs/testing.md` and `.github/workflows/`).

## Recommendations for production

- Use a strong, unique `SECRET_KEY` (e.g. `openssl rand -hex 32`).
- Terminate TLS and enforce HSTS.
- Add general API rate limiting and request-size limits.
- Add SSO (OIDC) and MFA.
- Run the API and workers as non-root (the Dockerfile already does this).
- Enable and ship OpenTelemetry traces and structured logs to a central store.
- Add a CI secret-scanning step (e.g. `gitleaks` / `trufflehog`).
