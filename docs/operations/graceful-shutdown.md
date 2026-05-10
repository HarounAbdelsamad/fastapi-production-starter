# Graceful Shutdown

The server must stop cleanly: finish in-flight requests, close DB connections, flush
telemetry spans, and drain queue workers — without dropping traffic or corrupting state.

## How it works

Uvicorn catches `SIGTERM` (from Docker / Kubernetes) and begins shutdown:

1. Stops accepting new connections.
2. Waits for in-flight HTTP requests to complete (up to `--timeout-graceful-shutdown`).
3. Runs the FastAPI lifespan `shutdown` block (the code after `yield` in `lifespan()`).

The lifespan shutdown block:
- Logs the shutdown with the configured grace period.
- Closes the Redis connection pool (`close_redis()`).
- Allows SQLAlchemy's async engine to be garbage-collected normally.

```python
# app/main.py (excerpt)
yield
logger.info("Shutting down %s — grace period %ss", ...)
await close_redis()
logger.info("Shutdown complete")
```

## Configuration

```bash
SHUTDOWN_GRACE_SECONDS=30   # logged; set uvicorn flag to match (see below)
```

When running uvicorn directly, pass the matching flag:

```bash
uvicorn app.main:app --timeout-graceful-shutdown 30
```

In Docker Compose / Kubernetes, set `stop_grace_period` / `terminationGracePeriodSeconds`
to `SHUTDOWN_GRACE_SECONDS + 5` to give the process time to exit cleanly before the
container is force-killed.

## Celery workers

Celery workers need their own graceful shutdown.  Send `SIGTERM` to let the worker
finish its current task before exiting:

```bash
# Graceful — finishes current task
celery -A app.worker control shutdown

# Immediate — abandons current task (use as last resort)
kill -9 <worker-pid>
```

Set `--max-tasks-per-child` to recycle workers periodically and avoid memory leaks:

```bash
celery -A app.worker worker --max-tasks-per-child=100
```

## Kubernetes rolling deployments

```yaml
spec:
  terminationGracePeriodSeconds: 35   # > SHUTDOWN_GRACE_SECONDS
  containers:
    - name: api
      lifecycle:
        preStop:
          exec:
            command: ["sleep", "5"]   # let the LB drain before SIGTERM
```

The `preStop` sleep gives the load balancer time to stop routing traffic before uvicorn
starts shutting down.

## OpenTelemetry span flushing

The `BatchSpanProcessor` flushes pending spans when `TracerProvider.shutdown()` is
called.  With the OTel SDK enabled, add this to the lifespan shutdown block if you need
guaranteed span delivery:

```python
from opentelemetry import trace
trace.get_tracer_provider().shutdown()
```

This is a no-op when `OTEL_SDK_DISABLED=true`.
