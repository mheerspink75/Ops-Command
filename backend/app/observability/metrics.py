"""Prometheus-compatible metrics.

Low-cardinality labels only: method, status class, task name, and result.
User ids, incident ids, emails, and raw paths are never used as labels.
"""

from __future__ import annotations

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

REGISTRY = CollectorRegistry()

HTTP_REQUESTS_TOTAL = Counter(
    "opscommand_http_requests_total",
    "Total HTTP requests",
    ["method", "status_class"],
    registry=REGISTRY,
)
HTTP_REQUEST_DURATION = Histogram(
    "opscommand_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "status_class"],
    registry=REGISTRY,
)
WORKER_TASKS_TOTAL = Counter(
    "opscommand_worker_tasks_total",
    "Background worker tasks",
    ["task", "result"],
    registry=REGISTRY,
)
WORKER_TASK_DURATION = Histogram(
    "opscommand_worker_task_duration_seconds",
    "Background worker task duration",
    ["task"],
    registry=REGISTRY,
)
WS_CONNECTIONS = Gauge(
    "opscommand_websocket_connections",
    "Active WebSocket connections",
    registry=REGISTRY,
)
PLAYBOOK_RUNS_TOTAL = Counter(
    "opscommand_playbook_runs_total",
    "Playbook runs by result",
    ["result"],
    registry=REGISTRY,
)


def status_class(status_code: int) -> str:
    return f"{status_code // 100}xx"


def record_http_request(method: str, status_code: int, duration_seconds: float) -> None:
    sc = status_class(status_code)
    HTTP_REQUESTS_TOTAL.labels(method=method, status_class=sc).inc()
    HTTP_REQUEST_DURATION.labels(method=method, status_class=sc).observe(duration_seconds)


def record_worker_task(task: str, result: str, duration_seconds: float) -> None:
    WORKER_TASKS_TOTAL.labels(task=task, result=result).inc()
    WORKER_TASK_DURATION.labels(task=task).observe(duration_seconds)


def record_playbook_run(result: str) -> None:
    PLAYBOOK_RUNS_TOTAL.labels(result=result).inc()


def set_ws_connections(count: int) -> None:
    WS_CONNECTIONS.set(count)


def render_metrics() -> bytes:
    return generate_latest(REGISTRY)
