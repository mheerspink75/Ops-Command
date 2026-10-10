"""OpenTelemetry tracing setup.

Defaults to a lightweight console exporter so the local stack stays light. To
ship traces to a collector, set OTEL_EXPORTER_OTLP_ENDPOINT and switch the
exporter to OTLPSpanExporter (see docs/architecture.md).
"""

from __future__ import annotations

import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.config import get_settings

logger = logging.getLogger(__name__)

_provider: TracerProvider | None = None


def setup_tracing() -> TracerProvider | None:
    global _provider
    settings = get_settings()
    if not settings.otel_enabled:
        return None
    try:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        resource = Resource.create({"service.name": settings.app_name.lower()})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
        _provider = provider
        logger.info("OpenTelemetry tracing enabled (console exporter)")
        return provider
    except Exception:  # noqa: BLE001 - tracing must never block startup
        logger.warning("OpenTelemetry setup failed; continuing without tracing", exc_info=True)
        return None


def get_tracer(name: str = "opscommand"):
    return trace.get_tracer(name)
