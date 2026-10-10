# ADR-001: Organization-scoped, server-side authorization

**Status:** Accepted

## Context

OpsCommand is multi-tenant: many organizations use the same deployment. The
critical requirement is that no organization can read or write another
organization's data — including by guessing or replaying resource IDs in URLs.
The frontend is a convenience layer and cannot be trusted as a security
boundary.

## Decision

- Every org-scoped route is namespaced under
  `/api/v1/organizations/{org_id}/...`.
- A `get_org_context` dependency resolves the caller's **membership** in the
  target organization on every request. It returns **404** for an unknown org
  and **403** for a non-member, so cross-org access by ID is blocked.
- A `require_role(min_role)` dependency enforces a role hierarchy
  (`viewer < responder < administrator < owner`). Read access requires
  membership; write actions require at least `responder`.
- The frontend never makes authorization decisions; it only reflects what the
  API allows.

## Consequences

- Strong tenancy guarantee enforced in one place (the API), not scattered
  across the UI.
- Slightly more boilerplate per route (the `OrgContext` dependency), but this
  is exactly where the guarantee must live.
- Adding a new resource type requires wiring it through `OrgContext` — a
  small, reviewable step.

## Alternatives considered

- **Frontend-gated authorization** — rejected: the UI is not a security
  boundary and can be bypassed.
- **A single global role** — rejected: teams need per-organization roles.
- **Row-level security in Postgres** — a possible hardening layer, but the
  application-level membership check is sufficient and more portable for this
  scope.
