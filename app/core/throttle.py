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
