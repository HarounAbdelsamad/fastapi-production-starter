# Outgoing Webhooks

Webhooks let external systems subscribe to events produced by your API.  When an event
fires, the server POSTs a signed JSON payload to every registered URL.

## Registering an endpoint (admin only)

```http
POST /api/v1/webhooks/
Authorization: Bearer <admin-token>

{
  "url": "https://your-app.example.com/hooks/receive",
  "secret": "a-random-string-you-choose",
  "events": "*"
}
```

`events` accepts `"*"` (all events) or a comma-separated list:

```json
{ "events": "user.created,user.deleted,order.placed" }
```

## Payload format

```json
{
  "event": "user.created",
  "user_id": "u-abc123",
  "timestamp": "2026-01-01T12:00:00Z"
}
```

Every request includes:

| Header | Value |
|---|---|
| `Content-Type` | `application/json` |
| `X-Webhook-Event` | event name |
| `X-Webhook-Delivery` | unique delivery ID |
| `X-Webhook-Signature` | `sha256=<hex>` |

## Verifying the signature

```python
import hashlib, hmac

def verify(body: bytes, secret: str, signature: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

Always verify the signature before processing the payload.

## Retry schedule

On non-2xx response or network error the delivery is retried with exponential backoff:

| Attempt | Delay |
|---|---|
| 1 | 30 s |
| 2 | 2 m |
| 3 | 8 m |
| 4 | 32 m |
| 5 | — (marked `failed`) |

## Delivery log

```http
GET /api/v1/webhooks/deliveries/?endpoint_id=<id>&limit=50
```

Returns status (`pending`, `success`, `failed`), attempt count, HTTP response code,
and `next_retry_at`.

## Replaying a delivery

```http
POST /api/v1/webhooks/deliveries/{delivery_id}/replay
```

Resends the original payload immediately regardless of current status.  Use this after
fixing a broken receiver or to test idempotency.

## Firing events from application code

```python
from app.services import webhook_service

await webhook_service.dispatch_event(db, "user.created", {"user_id": user.user_id})
```

`dispatch_event` is fire-and-commit — it does not raise on delivery failure; all
outcomes are recorded in the delivery log.

## Disabling webhooks

Set `WEBHOOKS_ENABLED=false` to remove the webhook router entirely (no routes
registered, zero overhead).
