# ADR-011: Toggleable Features Pattern (Env-Time vs Runtime)

## Status
Accepted

## Context

This template ships many optional features: rate limiting, caching, Celery queues, OpenTelemetry exporters, SAML, OAuth, WebSockets, feature flags, storage backends. Different deployments need different subsets enabled.

There are two distinct toggle mechanisms:

1. **Env-time (startup) toggles**: Configuration is read at application startup from environment variables. Changing a toggle requires a restart.
2. **Runtime toggles**: Configuration is stored in the database (or a cache) and can be changed without a restart.

Many templates conflate these or use only one. This ADR defines when each is appropriate and how they are implemented.

## Decision

**Use a two-tier system:**
- **Env-time toggles** for infrastructure features (things that affect how the app starts up)
- **Runtime feature flags** for business features (things that can safely change while the app runs)

## Tier 1: Env-Time Toggles

Env-time toggles control infrastructure-level features. These require application startup to activate because they affect how the ASGI app, middleware stack, connection pools, or background workers are initialized.

| Feature | Env key | Notes |
|---|---|---|
| Rate limiting | `RATE_LIMIT_ENABLED` | Adds middleware at startup; requires Redis if enabled |
| Redis cache | `CACHE_ENABLED` | Initializes Redis connection pool at startup |
| Celery queues | `CELERY_ENABLED` | Initializes Celery app and broker connection |
| Prometheus metrics | `METRICS_ENABLED` | Adds `/metrics` route and instrumentation at startup |
| WebSocket support | `WEBSOCKET_ENABLED` | Adds WebSocket router and connection manager |
| OAuth providers | `OAUTH_GOOGLE_ENABLED`, etc. | Adds OAuth routes and provider config |
| SAML | `SAML_ENABLED` | Adds SAML middleware and ACS route |
| OTLP export | `OTLP_ENDPOINT` | If set, sends telemetry to that endpoint |
| Storage backend | `STORAGE_BACKEND` | `local`, `s3`, `gcs` — affects how uploads are stored |

**Why restart is acceptable**: Infrastructure-level changes (adding a Redis connection pool, registering a new middleware) affect every request that flows through the app. They are not safely hot-swappable without careful state management. The trade-off (restart required) is accepted in exchange for simplicity and safety.

**Implementation**: Settings are validated via Pydantic at startup. If `CACHE_ENABLED=true` but `REDIS_URL` is not set, the app fails to start with a clear error message. This is intentional — "fail loudly at startup" rather than "fail silently at request time."

The `make check-config` command validates the configuration before deployment:
```bash
$ make check-config
Checking config for CACHE_ENABLED=true...
  ERROR: REDIS_URL is required when CACHE_ENABLED=true
  ERROR: REDIS_PASSWORD is required in production (ENVIRONMENT=production)
```

## Tier 2: Runtime Feature Flags

Runtime feature flags control business-level features that can change while the app is running. They are stored in the database and evaluated per-request.

**When runtime flags are appropriate:**
- Gradual rollouts ("enable feature X for 10% of users")
- Per-tenant feature access (tenant A has feature Y; tenant B does not)
- A/B testing
- Kill switches for new features (enable if works; disable immediately if breaks)
- Admin-controlled features (a super admin enables/disables features via the admin panel)

**Implementation:**

```sql
CREATE TABLE feature_flags (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id  UUID REFERENCES tenants(id),  -- NULL = global flag
    flag_key   VARCHAR(100) NOT NULL,
    enabled    BOOLEAN NOT NULL DEFAULT false,
    rollout_pct INT NOT NULL DEFAULT 100,    -- 0-100
    metadata   JSONB,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_by UUID  -- audit: who changed this
);

CREATE UNIQUE INDEX idx_feature_flags_key ON feature_flags(tenant_id, flag_key);
```

**Evaluation:**

```python
async def is_enabled(
    flag: str,
    tenant_id: UUID | None = None,
    user_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> bool:
    # 1. Check tenant-specific override
    if tenant_id:
        tenant_flag = await get_flag(db, flag, tenant_id)
        if tenant_flag:
            return evaluate_rollout(tenant_flag, user_id)
    # 2. Check global flag
    global_flag = await get_flag(db, flag, tenant_id=None)
    if global_flag:
        return evaluate_rollout(global_flag, user_id)
    # 3. Default to disabled
    return False
```

**Cache layer**: Feature flags are cached in Redis (or in-process LRU cache if Redis is disabled) with a configurable TTL (default: 60 seconds). This means flag changes propagate within 60 seconds without a DB query on every request.

**Admin endpoint**: `/api/v1/admin/features` allows super-admins to enable/disable flags and set rollout percentages without a deployment.

## What Tier Does NOT Cover

Env-time toggles are not feature flags. Feature flags are not env-time toggles. The confusion often comes from calling both "feature toggles" — this template uses distinct terminology:

- **Env-time toggle**: Controls infrastructure. Requires restart. Examples: rate limiting, Redis cache.
- **Runtime feature flag**: Controls business logic. No restart. Examples: "new dashboard UI", "enhanced search".

Runtime feature flags are **not** a replacement for proper configuration management. They are appropriate for short-lived, reversible changes. Long-term configuration (database URLs, auth providers, signing keys) belongs in env-time settings, not runtime flags.

## Consequences

**Positive:**
- Infrastructure features fail loudly at startup if misconfigured. No runtime surprises.
- Business features can be toggled without a deployment or restart.
- Per-tenant feature access is a first-class concept — important for enterprise B2B.
- `make check-config` catches configuration errors before they reach production.

**Negative:**
- Two distinct mechanisms adds mental overhead. Documented explicitly with the rule: "changes that require code path changes at startup → env-time; everything else → runtime flag."
- Runtime flags add a DB query (or cache read) per flag evaluation per request. Mitigated by the cache layer; documented as a consideration for high-cardinality flag usage.
- Runtime flag evaluation at 100% scale requires careful cache sizing. Per-tenant cardinality can be large. The template warns if flag count × tenant count exceeds a configurable threshold.
