"""Sanitization of audit details and log payloads.

Guarantees that passwords, bearer/refresh tokens, secrets, and full
authorization headers never appear in audit records or structured logs.
"""

from __future__ import annotations

from typing import Any

# Keys whose values must be redacted wherever they appear (case-insensitive).
_SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "passwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "auth",
    "api_key",
    "apikey",
    "private_key",
    "credential",
    "credentials",
    "session",
    "cookie",
}

_REDACTED = "***REDACTED***"


def _is_sensitive(key: str) -> bool:
    return key.lower() in _SENSITIVE_KEYS


def sanitize_value(value: Any) -> Any:
    """Recursively redact sensitive keys in dicts and lists."""
    if isinstance(value, dict):
        return {k: (_REDACTED if _is_sensitive(k) else sanitize_value(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_value(v) for v in value]
    return value


def sanitize_detail(detail: dict[str, Any] | None) -> dict[str, Any]:
    """Return a sanitized copy of an audit detail dict (never mutates input)."""
    if not detail:
        return {}
    return sanitize_value(detail)


def sanitize_headers(headers: dict[str, str] | None) -> dict[str, str]:
    """Redact sensitive headers (e.g. Authorization) for logging."""
    if not headers:
        return {}
    return {k: (_REDACTED if _is_sensitive(k) else v) for k, v in headers.items()}
