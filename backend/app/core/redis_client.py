"""Shared Redis client (lazy, cached)."""

from __future__ import annotations

from functools import lru_cache

import redis

from app.config import get_settings


@lru_cache
def get_redis() -> redis.Redis:
    settings = get_settings()
    return redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


def reset_redis() -> None:
    get_redis.cache_clear()
