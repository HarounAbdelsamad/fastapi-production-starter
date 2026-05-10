import time

from fastapi import HTTPException, status

from app.core.cache import get_redis
from app.core.config import get_settings

_attempts: dict[str, tuple[int, float]] = {}


async def check_login_throttle(username: str) -> None:
    settings = get_settings()
    key = f"login_attempts:{username}"
    redis = await get_redis()
    if redis is not None:
        attempts = await redis.incr(key)
        if attempts == 1:
            await redis.expire(key, settings.LOGIN_LOCKOUT_SECONDS)
        if attempts > settings.LOGIN_MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts, try again later",
            )
        return

    now = time.time()
    count, started_at = _attempts.get(username, (0, now))
    if now - started_at > settings.LOGIN_LOCKOUT_SECONDS:
        count, started_at = 0, now
    count += 1
    _attempts[username] = (count, started_at)
    if count > settings.LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts, try again later",
        )


async def reset_login_throttle(username: str) -> None:
    key = f"login_attempts:{username}"
    redis = await get_redis()
    if redis is not None:
        await redis.delete(key)
        return
    _attempts.pop(username, None)


# ---------------------------------------------------------------------------
# Advanced rate-limit key functions for SlowAPI
# ---------------------------------------------------------------------------
# Usage with per-endpoint limits:
#
#   from app.core.throttle import get_user_key
#   from app.core.rate_limit import limiter
#
#   @router.post("/send-email")
#   @limiter.limit("5/minute", key_func=get_user_key)
#   async def send_email(request: Request, ...): ...
#
# See docs/compliance/rate-limiting.md for the full three-layer guide.


def _ip_fallback(request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_key(request) -> str:
    """Per-user rate-limit key. Falls back to IP for unauthenticated requests."""
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "user_id"):
        return f"user:{user.user_id}"
    return _ip_fallback(request)


def get_tenant_key(request) -> str:
    """Per-tenant rate-limit key. Falls back to IP when tenant context is absent."""
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "tenant_id") and user.tenant_id:
        return f"tenant:{user.tenant_id}"
    return _ip_fallback(request)
