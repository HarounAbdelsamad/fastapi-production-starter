# Metrics — RED and USE

The API exposes Prometheus metrics at `/metrics` when `METRICS_ENABLED=true`. Metrics are collected by [prometheus-fastapi-instrumentator](https://github.com/trallnag/prometheus-fastapi-instrumentator).

## Enabling metrics

```bash
METRICS_ENABLED=true  # exposes /metrics (excluded from OpenAPI docs)
```

## RED method (per API endpoint)

**Rate · Errors · Duration** — the three metrics that answer "is the service healthy?"

| Signal | Prometheus query | What it tells you |
|---|---|---|
| **Rate** | `sum(rate(http_requests_total[5m]))` | Requests per second — drops signal a problem |
| **Error rate** | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` | Fraction of 5xx responses — spikes = something is broken |
| **Duration P95** | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` | 95th-percentile latency — tail latency matters more than average |
| **Duration P99** | `histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` | 99th percentile — worst-case user experience |

Break these down by handler for per-route visibility:

```promql
# Error rate per endpoint
sum by (handler) (rate(http_requests_total{status=~"5.."}[5m]))
  /
sum by (handler) (rate(http_requests_total[5m]))

# P95 latency per endpoint
histogram_quantile(0.95,
  sum by (handler, le) (rate(http_request_duration_seconds_bucket[5m]))
)
```

## USE method (infrastructure)

**Utilization · Saturation · Errors** — the three metrics that answer "is the infrastructure healthy?"

Apply this to every resource the API depends on:

### Database connection pool

| Signal | Query (needs SQLAlchemy pool metrics or custom gauge) |
|---|---|
| Utilization | `db_pool_checked_out / db_pool_size` |
| Saturation | `db_pool_overflow` — non-zero means pool is exhausted |
| Errors | `rate(db_query_errors_total[5m])` |

SQLAlchemy pool metrics require a custom Prometheus collector — see [connection pooling guide](../databases/connection-pooling.md).

### Redis

| Signal | Notes |
|---|---|
| Utilization | Memory used vs `maxmemory` — query Redis INFO via exporter |
| Saturation | `redis_blocked_clients` — clients waiting on BLPOP etc. |
| Errors | `redis_rejected_connections_total` |

For Redis metrics, run the [Redis Prometheus exporter](https://github.com/oliver006/redis_exporter) alongside Redis.

## Metrics reference

All metrics are prefixed with the instrumentator defaults. Labels: `method`, `handler`, `status`.

| Metric | Type | Description |
|---|---|---|
| `http_requests_total` | Counter | Total requests by method, handler, status |
| `http_request_duration_seconds` | Histogram | Request duration. Buckets: 0.005–10s |
| `http_request_size_bytes` | Histogram | Request body size |
| `http_response_size_bytes` | Histogram | Response body size |

## Alert rules

Copy these into a Prometheus rules file for basic coverage:

```yaml
groups:
  - name: fastapi
    rules:
      - alert: HighErrorRate
        expr: >
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Error rate above 5%"

      - alert: HighP99Latency
        expr: >
          histogram_quantile(0.99,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
          ) > 2.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P99 latency above 2 seconds"

      - alert: ServiceDown
        expr: up{job="fastapi"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "FastAPI service is unreachable"
```

## Grafana dashboard

The reference dashboard at [monitoring/grafana/dashboards/api.json](../../monitoring/grafana/dashboards/api.json) is provisioned automatically when you start the observability stack.

It includes:
- Four stat panels (req/s, error rate, P95, P99)
- Request rate broken down by HTTP status code
- Latency percentiles over time (P50, P95, P99)
- Per-handler request rate and error rate
- Request and response size percentiles
