# Architecture Decision Records

This directory contains short **Architecture Decision Records (ADRs)** that
capture the significant technical decisions behind OpsCommand and the context
for them.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](ADR-001-organization-scoped-authorization.md) | Organization-scoped, server-side authorization | Accepted |
| [ADR-002](ADR-002-realtime-hub-redis-bridge.md) | Real-time delivery via in-process hub + Redis pub/sub bridge | Accepted |
| [ADR-003](ADR-003-durable-playbook-execution.md) | Durable playbook execution with Celery + idempotency | Accepted |
| [ADR-004](ADR-004-optimistic-concurrency.md) | Optimistic concurrency for incident mutations | Accepted |
| [ADR-005](ADR-005-jwt-access-refresh-argon2.md) | JWT access/refresh tokens with Argon2 password hashing | Accepted |
| [ADR-006](ADR-006-mock-webhook.md) | Deterministic mock webhook for self-contained playbooks | Accepted |

## Format

Each ADR records: **Context** (the problem and forces), **Decision** (what we
chose), **Consequences** (trade-offs and follow-ups), and **Alternatives
considered**.
