# OpenTelemetry

This project ships with the OpenTelemetry SDK wired in by default. When no OTLP endpoint is configured the SDK is active but exports nothing — zero network overhead, full trace-ID propagation into logs.

## Architecture Decision

See [ADR-007](../adr/007-opentelemetry-default.md) for the reasoning behind "SDK on by default, exporter off by default."

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `OTLP_ENDPOINT` | `""` | OTLP gRPC endpoint (e.g. `http://jaeger:4317`). Empty = noop. |
| `OTEL_SDK_DISABLED` | `false` | Set `true` to skip SDK setup entirely. Removes all overhead. |
| `OTEL_SAMPLE_RATE` | `1.0` | Fraction of traces to sample (`1.0` = 100%, `0.1` = 10%). Uses `ParentBased(TraceIdRatioBased)`. |

## Instrumented libraries

When the SDK is active the following libraries are auto-instrumented:

| Library | Spans emitted |
|---|---|
| FastAPI (ASGI) | One span per HTTP request with method, route, status code |
| SQLAlchemy | One span per DB statement with sanitised SQL and table |
| Redis | One span per command (enabled only when `CACHE_ENABLED=true`) |
| Celery | Task enqueue + execution spans (enabled only when `CELERY_ENABLED=true`) |

## Trace ID in logs

Every log line written while a request is active includes `trace_id` and `span_id`. In JSON log format:

```json
{
  "timestamp": "2026-05-05T12:00:00.000000+00:00",
  "level": "INFO",
  "logger": "app.routers.auth",
  "message": "Login attempt for user@example.com",
  "request_id": "a1b2c3d4e5f6",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7"
}
```

This lets you jump from a log line directly to the full trace in Jaeger.

## Quick start (local)

```bash
# 1. Start the observability stack
docker compose --profile observability up -d

# 2. Configure the API to export traces
echo "OTLP_ENDPOINT=http://localhost:4317" >> .env
echo "METRICS_ENABLED=true" >> .env

# 3. Start the API
make run

# 4. Make a request
curl http://localhost:8000/health/live

# 5. Open Jaeger UI
open http://localhost:16686
```

## Sampling

Use `OTEL_SAMPLE_RATE` to reduce trace volume in high-traffic production environments:

```bash
# Sample 10% of traces
OTEL_SAMPLE_RATE=0.1

# Always sample (default — appropriate for low-to-medium traffic)
OTEL_SAMPLE_RATE=1.0
```

The sampler is `ParentBased(TraceIdRatioBased)`. This means:
- If an incoming request carries a parent trace, sampling follows the parent's decision.
- If no parent trace is present, sampling is probabilistic at the configured rate.

This ensures that a full distributed trace is either fully sampled or fully dropped — you never get orphan spans.

## Sequence diagram

```
Client → FastAPI → SQLAlchemy → Postgres
  │          │          │
  │     [root span]     │
  │          ├──────────►
  │          │     [db.query span]
  │          │          │
  │          │◄─────────┤
  │◄─────────┤
  │     response + X-Request-ID header
```

The trace ID is the same across all spans in the chain. Logs emitted during any span include that trace ID.

## Adding custom spans

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def my_service_call():
    with tracer.start_as_current_span("my_service_call") as span:
        span.set_attribute("service.name", "payments")
        result = await do_the_work()
        span.set_attribute("result.count", len(result))
        return result
```

## Per-tenant cardinality

If you add `tenant_id` as a span attribute or metric label, be aware of **cardinality explosion**: each unique tenant creates a new time series in Prometheus. For more than a few hundred tenants this becomes expensive.

**Recommended approach:**
- Add `tenant_id` to spans (Jaeger handles high cardinality well).
- Do **not** add `tenant_id` as a Prometheus label on high-frequency metrics.
- Instead, aggregate per-tenant metrics at query time from traces (Grafana Tempo + TraceQL).
