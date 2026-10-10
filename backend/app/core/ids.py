"""Request / correlation id helpers."""

from __future__ import annotations

import uuid


def new_request_id() -> str:
    return uuid.uuid4().hex


def normalize_request_id(value: str | None) -> str:
    """Return a sanitized request id, generating one if absent/invalid."""
    if value and 8 <= len(value) <= 64 and value.replace("-", "").isalnum():
        return value
    return new_request_id()
