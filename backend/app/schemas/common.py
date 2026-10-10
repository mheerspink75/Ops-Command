"""Shared schema types: pagination envelope and error envelope."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):  # noqa: UP046 - Pydantic requires the Generic base class
    items: list[T]
    total: int
    limit: int
    offset: int
    has_more: bool = False


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = {}


class ErrorEnvelope(BaseModel):
    error: ErrorDetail
