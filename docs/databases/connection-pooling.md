# Connection Pooling

SQLAlchemy manages a connection pool automatically. This page documents how pool parameters map to real deployments and how to tune them per database.

---

## How the Pool Works

SQLAlchemy's async engine maintains a pool of open database connections. When a request arrives:

1. A connection is checked out from the pool.
2. The request handler uses it via `AsyncSession`.
3. The connection is returned to the pool when the session closes (end of the `async with` block).

If the pool is exhausted (all connections checked out), new requests queue until a connection is released. If the queue waits longer than `pool_timeout` (default: 30 seconds), SQLAlchemy raises `TimeoutError`.

---

## Configuration Parameters

Set these in your `.env` file or environment:

| Variable | Default | Description |
|---|---|---|
| `DB_POOL_SIZE` | `5` | Number of persistent connections kept open. |
| `DB_MAX_OVERFLOW` | `10` | Additional connections allowed beyond `DB_POOL_SIZE` when the pool is full. Total max: `DB_POOL_SIZE + DB_MAX_OVERFLOW`. |

These are applied in `app/db/database.py` via `_build_engine()`.

SQLite does not use a connection pool (it uses a single file-level lock). Pool parameters are ignored for SQLite.

---

## Sizing the Pool

### Formula

```
Pool size ≥ (concurrent requests at peak) / (avg queries per request)
```

More practically:

```
DB_POOL_SIZE = workers × avg_db_connections_per_request × 1.2 (safety margin)
DB_MAX_OVERFLOW = DB_POOL_SIZE × 0.5
```

### Scale Tiers

The `SCALE_TIER` setting applies sensible defaults:

| Tier | `DB_POOL_SIZE` | `DB_MAX_OVERFLOW` | Use case |
|---|---|---|---|
| `basic` (default) | 5 | 10 | Development, low-traffic services |
| `standard` | 20 | 20 | Mid-traffic APIs (< 100 req/s) |
| `advanced` | 50 | 50 | High-traffic APIs (100–500 req/s) |
| `enterprise` | 100 | 100 | Very high traffic or many tenants |

Set `SCALE_TIER=standard` (or higher) in production rather than manually tuning pool sizes.

### PostgreSQL-Specific

PostgreSQL has a `max_connections` server parameter (default: 100 on most managed services; 200–500 on self-hosted). If you deploy multiple app instances, **the total connections across all instances must not exceed the server limit**:

```
Total connections = (instances × (DB_POOL_SIZE + DB_MAX_OVERFLOW)) ≤ max_connections
```

Example: 4 app instances with `DB_POOL_SIZE=20, DB_MAX_OVERFLOW=20`:

```
4 × (20 + 20) = 160 connections
```

If your Postgres `max_connections=100`, this will overflow. Either:
- Reduce pool size per instance: `DB_POOL_SIZE=10, DB_MAX_OVERFLOW=15`
- Use PgBouncer as a connection multiplexer (see below)
- Increase Postgres `max_connections` (requires server restart)

### MySQL-Specific

MySQL's default `max_connections` is 151. The same calculation applies. MySQL is generally more tolerant of connection-per-thread overhead than Postgres, but large pools still consume server memory.

---

## Read Replicas

If you configure `DB_READ_REPLICA_URL`, the template creates a separate pool for the read replica:

```bash
DB_READ_REPLICA_URL=postgresql+asyncpg://user:pass@replica-host:5432/dbname
```

Use `get_read_session` (instead of `get_session`) in route handlers that only need read access:

```python
from app.db.database import get_read_session

@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_read_session),  # reads from replica
):
    ...
```

The read replica pool uses the same `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` settings. If you need different sizing for the replica pool, configure it directly in `app/db/database.py`.

---

## PgBouncer (Connection Multiplexer)

For high-traffic Postgres deployments with many app instances, PgBouncer reduces the actual number of server connections by multiplexing:

```
App instances × pool_size → PgBouncer → Postgres max_connections
```

PgBouncer sits between the app and Postgres. The `DATABASE_URL` points to PgBouncer:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@pgbouncer:6432/dbname
```

**Important**: PgBouncer in `transaction` pooling mode is not compatible with prepared statements. Configure `asyncpg` to disable them:

```python
# In _build_engine(), add to connect_args:
connect_args["prepared_statement_cache_size"] = 0
connect_args["statement_cache_size"] = 0
```

This is documented but not the default, as most deployments don't need PgBouncer.

---

## Pool Health and Monitoring

### Detecting Pool Exhaustion

Pool exhaustion manifests as:
- `TimeoutError: QueuePool limit of size X overflow Y reached` in logs
- Increased latency on all requests (they're queuing)
- Prometheus metric `sqlalchemy_pool_checkedout` approaching `pool_size + max_overflow`

### Prometheus Metrics

With `METRICS_ENABLED=true`, SQLAlchemy pool metrics are exposed at `/metrics`:

```
sqlalchemy_pool_size            — configured pool size
sqlalchemy_pool_checkedout      — connections currently in use
sqlalchemy_pool_overflow        — overflow connections in use
sqlalchemy_pool_checkedin       — connections idle in pool
```

Set an alert when `sqlalchemy_pool_checkedout / (pool_size + max_overflow) > 0.8` for more than 1 minute.

### Pool Recycle

Connections are recycled (replaced) by default after they have been idle for 1 hour. This prevents stale connections from hitting a server-side `wait_timeout` (MySQL default: 8 hours). Set explicitly if your DB has a shorter idle timeout:

```python
# In _build_engine():
engine_kwargs["pool_recycle"] = 3600  # seconds
```

---

## Connection Pool and Alembic Migrations

Alembic uses a **separate synchronous connection** for migrations, not the async pool. The async pool is for runtime request handling only. Migrations can run while the app is serving traffic (for online migrations).

For long-running migrations (backfills), run them as a separate process, not during `alembic upgrade head`. See [zero-downtime migrations](../migrations/zero-downtime.md).
