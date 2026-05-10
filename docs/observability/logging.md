# Structured Logging

## Format

Two formats are available, selected by `LOG_FORMAT`:

| Value | Format | Use case |
|---|---|---|
| `text` (default) | `YYYY-MM-DD HH:MM:SS \| LEVEL \| logger \| request_id \| message` | Local development |
| `json` | JSON object per line | Production / log aggregation (Loki, CloudWatch, Datadog) |

```bash
LOG_FORMAT=json  # enable JSON output
```

### JSON log line

```json
{
  "timestamp": "2026-05-05T12:00:00.123456+00:00",
  "level": "INFO",
  "logger": "app.routers.auth",
  "message": "Login successful",
  "request_id": "a1b2c3d4e5f6",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7"
}
```

`trace_id` and `span_id` are populated from the active OpenTelemetry span. When no span is active (e.g., background tasks not within a trace), both fields contain `"-"`.

## Trace ID correlation

When `OTLP_ENDPOINT` is configured and the observability stack is running, you can jump from a log line to its full trace:

1. Find a log entry in Grafana/Loki
2. Copy the `trace_id` value
3. Open Jaeger → Search → Trace ID → paste
4. See the full span tree with DB queries, Redis calls, etc.

Grafana can automate this via the Loki ↔ Jaeger trace-to-logs correlation configured in `monitoring/grafana/provisioning/datasources/datasources.yml`.

## Log levels

| Level | Usage |
|---|---|
| `DEBUG` | Detailed internal state. Enable with `DEBUG=true`. Off by default. |
| `INFO` | Normal operational events (startup, shutdown, requests). |
| `WARNING` | Unexpected but recoverable conditions (deprecated usage, fallbacks). |
| `ERROR` | Failures that affect the current operation but not the process. |
| `CRITICAL` | Failures that may require human intervention. |

Set `DEBUG=true` to enable debug-level logging. This also enables SQLAlchemy query logging.

## Noisy loggers silenced by default

When `DEBUG=false` (the default), the following loggers are set to `WARNING`:

- `sqlalchemy.engine` — suppresses SQL echo
- `uvicorn.access` — access log noise

## PII redaction

Enable automatic PII scrubbing from log messages:

```bash
LOG_PII_REDACT=true
```

When enabled, the following patterns are replaced in all log messages:

| Pattern | Replacement |
|---|---|
| Email addresses | `[email]` |
| Credit card numbers | `[card]` |
| US phone numbers | `[phone]` |
| Social Security Numbers (SSN) | `[ssn]` |

**Example:**

```
# Without redaction
INFO: Login from user@company.com via 555-867-5309

# With LOG_PII_REDACT=true
INFO: Login from [email] via [phone]
```

**Limitations:**
- Pattern-based — cannot redact PII embedded in JSON values within a string.
- Regex matching has a small per-record cost; benchmark before enabling at very high log volumes.
- For structured PII redaction (field-level), tag fields on your Pydantic models and filter at serialization time instead.

## Loki integration

When the observability stack is running (`docker compose --profile observability up`), Promtail ships all Docker container logs to Loki. Query them in Grafana:

```logql
# All FastAPI logs
{container_name="fastapi_api"}

# Error logs only
{container_name="fastapi_api"} |= "ERROR"

# Logs for a specific trace
{container_name="fastapi_api"} | json | trace_id="4bf92f3577b34da6a3ce929d0e0e4736"
```

The last query requires `LOG_FORMAT=json` so Loki can parse the `trace_id` field.
