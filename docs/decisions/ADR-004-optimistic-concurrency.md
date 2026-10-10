# ADR-004: Optimistic concurrency for incident mutations

**Status:** Accepted

## Context

Multiple responders act on the same incident concurrently (status changes,
edits, role assignments). Without coordination, two writes can silently
clobber each other (last-write-wins), losing a responder's update. We want a
simple, correct mechanism that fails loudly on conflict rather than dropping
data.

## Decision

- `Incident` carries a `version` integer, incremented on each write.
- Mutating endpoints accept an `expected_version`. The service compares it to
  the current row version and raises a **conflict (409)** if they differ.
- The client re-reads the incident and retries with the fresh version.
- Status transitions additionally validate against the state machine
  (`VALID_TRANSITIONS`), so an invalid transition is rejected regardless of
  version.

## Consequences

- Concurrent edits are detected and surfaced to the user instead of silently
  lost.
- Simple to implement (a single integer column + a compare-and-set) and to
  reason about.
- Clients must handle 409 and re-fetch; this is a small, well-understood cost.

## Alternatives considered

- **Pessimistic row locking (`SELECT ... FOR UPDATE`)** — correct but holds
  locks across the request and is harder to use from a UI; optimistic
  concurrency fits the low-contention, high-read pattern better.
- **Last-write-wins** — rejected: silently loses updates, unacceptable for an
  incident command view.
- **CRDTs / operational transforms** — overkill for this data model.
