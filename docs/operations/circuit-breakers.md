# Circuit Breakers

A circuit breaker prevents cascading failures by stopping calls to a downstream service
that is known to be unhealthy, giving it time to recover.

## Three states

```
CLOSED ──(failures ≥ threshold)──► OPEN ──(recovery_timeout elapsed)──► HALF-OPEN
   ▲                                                                          │
   └──────────────────── (probe succeeds) ───────────────────────────────────┘
                         (probe fails → back to OPEN)
```

| State | Behaviour |
|---|---|
| **CLOSED** | Normal operation; failures increment a counter |
| **OPEN** | All calls rejected immediately with `CircuitBreakerOpen` |
| **HALF-OPEN** | One probe call allowed; success → CLOSED, failure → OPEN |

## Usage

```python
from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpen

# Create once at module level (or inject via dependency)
payments_breaker = CircuitBreaker(
    "payments-api",
    failure_threshold=5,    # 5 consecutive failures → OPEN
    recovery_timeout=60.0,  # wait 60 s before probing
)

# Context-manager style
async def call_payments(user_id: str):
    try:
        async with payments_breaker:
            return await httpx_client.post("https://payments.example.com/charge", ...)
    except CircuitBreakerOpen:
        raise HTTPException(503, "Payment service temporarily unavailable")

# Explicit call style
result = await payments_breaker.call(
    httpx_client.get("https://payments.example.com/status")
)
```

## Wiring into FastAPI

For app-wide breakers, initialise at startup and store on `app.state`:

```python
# app/main.py — inside create_app()
from app.core.circuit_breaker import CircuitBreaker

app.state.payments_breaker = CircuitBreaker("payments-api", failure_threshold=5)
```

Access in route handlers:

```python
@router.post("/checkout")
async def checkout(request: Request, ...):
    breaker: CircuitBreaker = request.app.state.payments_breaker
    try:
        async with breaker:
            result = await payments_client.charge(...)
    except CircuitBreakerOpen:
        raise HTTPException(503, "Payment service unavailable — try again shortly")
```

## Configuration reference

| Parameter | Default | Meaning |
|---|---|---|
| `failure_threshold` | `5` | Consecutive failures to open the circuit |
| `recovery_timeout` | `60.0` | Seconds in OPEN before probing |
| `half_open_max_calls` | `1` | Concurrent probe calls in HALF-OPEN |

## What counts as a failure

Any exception raised inside `call()` / `async with breaker:` increments the counter.
`CircuitBreakerOpen` itself is **not** counted (it means the circuit is already open).

To ignore specific exceptions (e.g. 404 Not Found is not a circuit failure):

```python
try:
    result = await breaker.call(client.get(url))
except httpx.HTTPStatusError as exc:
    if exc.response.status_code == 404:
        await breaker.record_success()   # 404 is not a health failure
        raise
    raise

```

## Observability

Log state transitions and emit metrics around calls:

```python
if breaker.state == "open":
    logger.warning("circuit %s is open", breaker.name)
```

Alert when a circuit stays open for more than `2 × recovery_timeout`.
