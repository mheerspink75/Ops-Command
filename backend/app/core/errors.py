"""Domain errors and a consistent API error envelope.

Every error raised from the domain layer is mapped to a stable HTTP status and
a JSON envelope: {"error": {"code": ..., "message": ..., "details": ...}}.
"""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base class for expected domain failures."""

    status_code: int = 400
    code: str = "domain_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_envelope(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class ValidationError(DomainError):
    status_code = 422
    code = "validation_error"


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ForbiddenError(DomainError):
    status_code = 403
    code = "forbidden"


class UnauthorizedError(DomainError):
    status_code = 401
    code = "unauthorized"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class InvalidTransitionError(DomainError):
    status_code = 422
    code = "invalid_transition"


class ConcurrencyError(DomainError):
    """Raised when an optimistic-concurrency version check fails."""

    status_code = 409
    code = "concurrency_conflict"


class RateLimitedError(DomainError):
    status_code = 429
    code = "rate_limited"
