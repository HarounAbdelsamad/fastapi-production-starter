# Observability Stack

The full observability stack runs as Docker Compose services under the `observability` profile. It includes Jaeger (traces), Prometheus (metrics), Grafana (dashboards), Loki (logs), and Promtail (log shipper).

## Quick start

```bash
# 1. Configure the API to export telemetry
cat >> .env <<'EOF'
OTLP_ENDPOINT=http://localhost:4317
METRICS_ENABLED=true
LOG_FORMAT=json
EOF

# 2. Start everything
docker compose --profile observability up -d

# 3. Send some traffic
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready

# 4. Open the UIs
open http://localhost:3000   # Grafana (admin / admin)
open http://localhost:16686  # Jaeger
open http://localhost:9090   # Prometheus
```

## Services

| Service | Port | Purpose |
|---|---|---|
| Jaeger | `16686` (UI), `4317` (OTLP gRPC), `4318` (OTLP HTTP) | Distributed trace storage and UI |
| Prometheus | `9090` | Metrics scraping and query engine |
| Grafana | `3000` | Unified dashboard for metrics + logs + traces |
| Loki | `3100` | Log aggregation backend |
| Promtail | — | Reads Docker container logs → ships to Loki |

## Data flow

```
FastAPI app
  ├── /metrics endpoint
  │       └── scraped by Prometheus every 15s
  ├── OTLP traces → Jaeger:4317
  │       └── visualised in Jaeger UI and Grafana
  └── stdout (JSON logs)
          └── Promtail reads container logs → Loki → Grafana
```

## Grafana dashboards

The `FastAPI — RED Dashboard` is provisioned automatically. It shows:

- Request rate, error rate, P95/P99 latency (stat panels)
- Request rate by HTTP status over time
- Latency percentiles (P50/P95/P99) over time
- Per-handler request rate and error rate
- Request/response size percentiles

Dashboard JSON lives at [monitoring/grafana/dashboards/api.json](../../monitoring/grafana/dashboards/api.json).

To add your own dashboards, drop JSON files into `monitoring/grafana/dashboards/`. They are provisioned on Grafana startup.

## Trace → Log correlation

Grafana is configured to link traces (Jaeger) to logs (Loki). Prerequisite: `LOG_FORMAT=json` so Loki can parse `trace_id` from log lines.

In Grafana, open a trace in the Explore panel. Click **Logs** next to any span to jump to Loki filtered by that trace ID.

## Volumes

Observability data is persisted in named Docker volumes:

| Volume | Contents |
|---|---|
| `promdata` | Prometheus TSDB (15-day retention by default) |
| `lokidata` | Loki log chunks |
| `grafanadata` | Grafana database (saved dashboards, alert configs) |

## Shutting down

```bash
# Stop observability stack only (keeps core services running)
docker compose --profile observability stop jaeger prometheus loki promtail grafana

# Remove observability stack and its data volumes
docker compose --profile observability down -v
```

## Production considerations

| Concern | Recommendation |
|---|---|
| Prometheus retention | Add `--storage.tsdb.retention.time=30d` to Prometheus args |
| Loki storage | Replace filesystem with S3 or GCS for durable, scalable log storage |
| Jaeger storage | Replace in-memory with Elasticsearch or Cassandra backend for large trace volumes |
| Grafana auth | Replace default `admin/admin` with LDAP/OAuth via `grafana.ini` |
| Scrape interval | Increase to 30s in low-traffic environments to reduce cardinality |
| Sampling rate | Set `OTEL_SAMPLE_RATE=0.1` (10%) in high-traffic production to reduce Jaeger load |
