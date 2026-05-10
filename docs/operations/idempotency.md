# Idempotency Keys

Idempotency keys let clients safely retry POST / PATCH requests without risking duplicate
side effects — creating two orders, sending two emails, charging a card twice.

## Client contract

Add the `Idempotency-Key` header with a UUID generated on the client side:

```http
POST /api/v1/orders/
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{ "product_id": "p-1", "quantity": 2 }
```

Rules:
- Generate a new UUID per _logical operation_, not per HTTP retry.
- Re-send the **same** key (and same request body) on retry.
- Keys are scoped to `method + path + key`, so the same UUID is safe across different
  endpoints.
- Keys expire after 24 hours (configurable via `IDEMPOTENCY_TTL`).

## Server behaviour

| Request | Response |
|---|---|
| First request with key | Normal processing; response stored |
| Retry with same key + path | Cached response; `X-Idempotent-Replayed: true` added |
| Different key | Independent request |
| GET / PUT / DELETE | Not guarded (safe / idempotent by spec) |

## Storage

The middleware stores `{status, body, content-type}` keyed on
`idempotency:{METHOD}:{path}:{key}`.

- **Redis** (when `CACHE_ENABLED=true`): shared across all instances, survives restarts.
- **In-process dict** (fallback): single instance only, resets on restart.

Use Redis in production.

## Configuration

```bash
IDEMPOTENCY_TTL=86400   # seconds (default: 24 h)
CACHE_ENABLED=true      # required for Redis-backed idempotency
REDIS_URL=redis://redis:6379/0
```

## Edge cases

**Concurrent retries**: if two identical requests arrive simultaneously before the first
completes, both are processed.  This is an inherent limitation of middleware-level
idempotency without distributed locking.  For strict exactly-once semantics, enforce
idempotency at the database layer (unique constraint on the idempotency key column).

**Body mismatch**: the middleware does not validate that the retry body matches the
original.  Stripe-style strict body matching requires storing the request body hash and
comparing it on replay — extend `IdempotencyMiddleware` if needed.

**Non-JSON responses**: the middleware stores the raw bytes and content-type, so file
uploads and streaming responses are also covered.
