"""OpenTelemetry SDK setup.

The SDK is wired in by default with no exporter (noop behavior) so trace IDs
are generated and propagated into logs without any network overhead.

To export traces, set OTLP_ENDPOINT (e.g. "http://jaeger:4317").
To disable the SDK entirely, set OTEL_SDK_DISABLED=true.

See docs/observability/otel.md for the full setup guide.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def setup_telemetry(app: Any, *, settings: Any) -> None:
    """Wire OpenTelemetry into the FastAPI application.

    Must be called before the first request is handled (i.e., from lifespan
    before yield). The app instance is mutated to add OTel middleware.
    """
    if settings.OTEL_SDK_DISABLED:
        logger.debug("OpenTelemetry SDK disabled via OTEL_SDK_DISABLED=true")
        return

    from opentelemetry import trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

    resource = Resource.create({SERVICE_NAME: settings.APP_TITLE})
    sampler = ParentBased(root=TraceIdRatioBased(settings.OTEL_SAMPLE_RATE))
    provider = TracerProvider(resource=resource, sampler=sampler)

    if settings.OTLP_ENDPOINT:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        exporter = OTLPSpanExporter(endpoint=settings.OTLP_ENDPOINT, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info(
            "OTel traces → %s (sample_rate=%.2f)",
            settings.OTLP_ENDPOINT,
            settings.OTEL_SAMPLE_RATE,
        )
    else:
        logger.debug("OTel SDK active; no OTLP_ENDPOINT — traces not exported (noop mode)")

    trace.set_tracer_provider(provider)

    # Instrument FastAPI — adds OTel middleware for per-request spans
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)

    # Instrument SQLAlchemy — emits DB spans on every query
    SQLAlchemyInstrumentor().instrument(tracer_provider=provider, enable_commenter=True)

    # Instrument Redis only when cache is enabled
    if settings.CACHE_ENABLED:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument(tracer_provider=provider)

    # Instrument Celery only when workers are enabled
    if settings.CELERY_ENABLED:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        CeleryInstrumentor().instrument()

    logger.debug("OpenTelemetry instrumentation active")
