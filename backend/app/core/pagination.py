"""Pagination helpers with a consistent response envelope."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field


class Page(BaseModel, generic=True):
    """Generic paginated response envelope."""

    items: list[Any]
    total: int
    limit: int
    offset: int
    has_more: bool = Field(default=False)


@dataclass(frozen=True)
class PageParams:
    limit: int
    offset: int


def clamp_page_params(limit: int, offset: int, max_limit: int = 200) -> PageParams:
    """Clamp pagination parameters to safe bounds (prevents unbounded queries)."""
    limit = max(1, min(limit, max_limit))
    offset = max(0, offset)
    return PageParams(limit=limit, offset=offset)


def paginate(items: Sequence[Any], total: int, limit: int, offset: int) -> dict[str, Any]:
    return {
        "items": list(items),
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    }
