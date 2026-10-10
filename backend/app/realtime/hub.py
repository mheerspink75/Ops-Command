"""Real-time event hub.

Delivers events to in-process WebSocket subscribers and, when a Redis URL is
configured, bridges events across backend processes via Redis pub/sub so that a
worker or another API process can publish to a room this process is serving.
"""

from __future__ import annotations

import json
import logging
import threading
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "opscommand:incident:"


class RealtimeHub:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[Callable[[dict[str, Any]], None]]] = defaultdict(set)
        self._lock = threading.Lock()
        self._bridge_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._connection_count = 0

    # --- In-process subscription ---
    def subscribe(self, incident_id: str, callback: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            self._subscribers[incident_id].add(callback)
            self._connection_count += 1

    def unsubscribe(self, incident_id: str, callback: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            subs = self._subscribers.get(incident_id)
            if subs and callback in subs:
                subs.discard(callback)
                self._connection_count = max(0, self._connection_count - 1)

    @property
    def connection_count(self) -> int:
        with self._lock:
            return self._connection_count

    # --- Publishing ---
    def publish(self, incident_id: str, event: dict[str, Any]) -> None:
        """Deliver to in-process subscribers and bridge to Redis (best effort)."""
        with self._lock:
            callbacks = list(self._subscribers.get(incident_id, ()))
        for cb in callbacks:
            try:
                cb(event)
            except Exception:  # noqa: BLE001 - one bad subscriber must not break others
                logger.exception("realtime subscriber error")
        self._redis_publish(incident_id, event)

    def _redis_publish(self, incident_id: str, event: dict[str, Any]) -> None:
        try:
            r = get_redis()
            r.publish(CHANNEL_PREFIX + incident_id, json.dumps(event, default=str))
        except Exception:  # noqa: BLE001 - Redis is optional for in-process delivery
            logger.debug("redis publish skipped", exc_info=True)

    # --- Redis bridge (cross-process) ---
    def start_redis_bridge(self) -> None:
        if self._bridge_thread is not None:
            return
        self._stop.clear()
        self._bridge_thread = threading.Thread(target=self._bridge_loop, daemon=True)
        self._bridge_thread.start()

    def stop_redis_bridge(self) -> None:
        self._stop.set()
        if self._bridge_thread is not None:
            self._bridge_thread.join(timeout=2)
            self._bridge_thread = None

    def _bridge_loop(self) -> None:
        try:
            r = get_redis()
            pubsub = r.pubsub()
            pubsub.psubscribe(CHANNEL_PREFIX + "*")
            for message in pubsub.listen():
                if self._stop.is_set():
                    break
                if message.get("type") != "pmessage":
                    continue
                channel: str = message.get("channel", "")
                data = message.get("data", "")
                incident_id = channel.replace(CHANNEL_PREFIX, "")
                try:
                    event = json.loads(data)
                except (ValueError, TypeError):
                    continue
                with self._lock:
                    callbacks = list(self._subscribers.get(incident_id, ()))
                for cb in callbacks:
                    try:
                        cb(event)
                    except Exception:  # noqa: BLE001
                        logger.exception("realtime bridge subscriber error")
        except Exception:  # noqa: BLE001
            logger.debug("redis bridge stopped", exc_info=True)


# Module-level singleton used by the app and worker.
hub = RealtimeHub()
