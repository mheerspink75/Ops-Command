"""Redis-backed login throttling (fixed window per identifier).

The identifier is a normalized email or username. Only failed attempts are
recorded, so legitimate users are not penalized for successful logins.
"""

from __future__ import annotations

import time

from app.config import get_settings
from app.core.errors import RateLimitedError
from app.core.redis_client import get_redis


def _key(identifier: str) -> str:
    return f"login_throttle:{identifier.lower()}"


def is_login_throttled(identifier: str) -> bool:
    settings = get_settings()
    r = get_redis()
    count = int(r.zcard(_key(identifier)))  # type: ignore[arg-type]
    return count >= settings.login_max_attempts


def record_login_failure(identifier: str) -> int:
    settings = get_settings()
    r = get_redis()
    now = time.time()
    window = settings.login_window_seconds
    key = _key(identifier)
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, now - window)
    pipe.zadd(key, {f"{now:.6f}": now})
    pipe.expire(key, window)
    pipe.zcard(key)
    _, _, _, count = pipe.execute()
    return int(count)


def clear_login_throttle(identifier: str) -> None:
    get_redis().delete(_key(identifier))


def check_or_raise(identifier: str) -> None:
    if is_login_throttled(identifier):
        raise RateLimitedError("Too many failed login attempts. Please wait before trying again.")
