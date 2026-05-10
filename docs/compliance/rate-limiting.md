# Rate Limiting

Three layers of rate limiting are supported, built on [SlowAPI](https://github.com/laurents/slowapi) (a Starlette/FastAPI adapter for `limits`).

## Layer 1 — Per-IP (global default)

Enabled via env:

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=60/minute   # applied to every route
RATE_LIMIT_AUTH=10/minute      # used by auth endpoints explicitly
```

When `CACHE_ENABLED=true` the counter is stored in Redis (supports multi-instance). Otherwise in-process memory (single instance only).

## Layer 2 — Per-user (authenticated endpoints)

Use `get_user_key` as the SlowAPI key function on any route:

```python
from fastapi import Request
from app.core.throttle import get_user_key
from app.core.rate_limit import limiter

@router.post("/send-notification")
@limiter.limit("5/minute", key_func=get_user_key)
async def send_notification(request: Request, ...):
    ...
```

`get_user_key` reads `request.state.user.user_id` if present; falls back to remote IP.

To populate `request.state.user`, set it in a middleware or dependency:

```python
# In a dependency or middleware, after auth resolves:
request.state.user = current_user
```

## Layer 3 — Per-tenant (multi-tenant deployments)

```python
from app.core.throttle import get_tenant_key

@router.post("/bulk-import")
@limiter.limit("10/hour", key_func=get_tenant_key)
async def bulk_import(request: Request, ...):
    ...
```

`get_tenant_key` reads `request.state.user.tenant_id`; falls back to IP. Requires the `User` model to carry `tenant_id` (via `TenantMixin`).

## Per-endpoint overrides

Override the global default on any individual route:

```python
@router.post("/login")
@limiter.limit("10/minute")          # stricter than global 60/minute
async def login(request: Request, ...):
    ...

@router.get("/health/live")
@limiter.limit("1000/minute")        # relaxed — health checks are high-frequency
async def liveness(request: Request, ...):
    ...
```

## Combining layers

Per-IP + per-user simultaneously (two separate decorators):

```python
@router.post("/api/v1/emails/send")
@limiter.limit("100/minute")                         # per-IP guard
@limiter.limit("10/minute", key_func=get_user_key)   # per-user guard
async def send_email(request: Request, ...):
    ...
```

The request is rejected when either limit is exceeded.

## Redis-backed counters (production)

Without Redis, counters are in-process memory and reset on restart. For multi-instance deployments:

```bash
CACHE_ENABLED=true
REDIS_URL=redis://redis:6379/0
RATE_LIMIT_ENABLED=true
```

When both flags are set, `get_limiter()` passes `storage_uri` to SlowAPI automatically.

## Rate limit response

Exceeded limits return HTTP 429:

```json
{
  "error": {
    "code": "TOO_MANY_REQUESTS",
    "message": "Rate limit exceeded",
    "request_id": "..."
  }
}
```

## Cardinality note

Per-tenant rate limiting creates one Redis key per tenant per window. For thousands of tenants this is fine. For millions, consider a tiered approach: per-IP at the load balancer, per-tenant only for expensive endpoints.
