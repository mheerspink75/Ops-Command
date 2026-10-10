# ADR-005: JWT access/refresh tokens with Argon2 password hashing

**Status:** Accepted

## Context

The API is stateless and must scale across replicas, so session cookies in a
shared store are undesirable. We need: strong password storage, short-lived
bearer tokens for API calls, a way to renew them without re-entering the
password, and the ability to revoke a session on logout.

## Decision

- **Passwords** are hashed with **Argon2id** (`argon2-cffi`); plaintext is
  never stored or logged.
- **Access tokens** are short-lived JWTs (default 15 min), signed with
  `SECRET_KEY` (HS256), carrying `sub` (user id) and `type: "access"`.
- **Refresh tokens** are long-lived (default 14 days), stored server-side,
  **rotated** on each refresh, and **revocable** on logout. Rotation makes a
  stolen refresh token single-use.
- **Login throttling** is per-identifier and Redis-backed (default 5 attempts
  / 60 s) to blunt brute force.
- A **production guard** refuses to boot with the insecure default
  `SECRET_KEY`.

## Consequences

- Stateless API auth that scales horizontally.
- Strong password hashing and revocable, rotating refresh tokens.
- Adds a server-side store for refresh tokens (a small, bounded table) and a
  dependency on Redis for throttling.

## Alternatives considered

- **Opaque session tokens in a DB/Redis** — viable, but JWT access tokens keep
  the hot path stateless; we keep refresh tokens server-side for revocation.
- **Passwordless / WebAuthn** — a good future direction, but out of scope for
  this reference implementation.
- **bcrypt** — acceptable, but Argon2id is the current recommended default and
  is memory-hard against GPU attacks.
