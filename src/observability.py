"""Observability utilities for tracing and metrics."""

import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, OTLPSpanExporter
from prometheus_client import Counter, Histogram, start_http_server


_tracer = None

# Prometheus metrics for database sync performance
DB_SYNC_COUNTER = Counter(
    "database_sync_total", "Total number of database sync operations"
)
DB_SYNC_DURATION = Histogram(
    "database_sync_seconds", "Duration of database sync operations"
)


def setup_tracing(service_name: str = "causaganha") -> None:
    """Initialize OpenTelemetry tracing."""
    global _tracer
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(__name__)
    logging.getLogger(__name__).info("OpenTelemetry tracing enabled")


def get_tracer():
    """Return the initialized tracer."""
    return _tracer or trace.get_tracer(__name__)


def setup_metrics(port: int = 8001) -> None:
    """Expose Prometheus metrics on the given port."""
    start_http_server(port)
    logging.getLogger(__name__).info("Prometheus metrics server running on %s", port)

