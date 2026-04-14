import json
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from redis.asyncio import Redis, from_url

from app.core.config import get_settings

_redis_client: Redis | None = None


async def get_redis() -> Redis | None:
    global _redis_client
    settings = get_settings()
    if not settings.CACHE_ENABLED:
        return None
    if _redis_client is None:
        _redis_client = from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


async def invalidate(pattern: str) -> None:
    redis = await get_redis()
    if redis is None:
        return
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)


def cache(ttl: int | None = None, key_prefix: str = "") -> Callable:
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            redis = await get_redis()
            settings = get_settings()
            if redis is None:
                return await func(*args, **kwargs)

            cache_key = f"{key_prefix}:{func.__name__}:{args[1:]}:{sorted(kwargs.items())}"
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)

            result = await func(*args, **kwargs)
            await redis.set(
                cache_key,
                json.dumps(result, default=str),
                ex=ttl or settings.CACHE_DEFAULT_TTL,
            )
            return result

        return wrapper

    return decorator
