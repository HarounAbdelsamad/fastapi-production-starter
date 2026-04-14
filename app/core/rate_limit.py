from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings


def get_limiter() -> Limiter:
    settings = get_settings()
    if not settings.RATE_LIMIT_ENABLED:
        return Limiter(key_func=get_remote_address, enabled=False, default_limits=[])
    kwargs: dict[str, object] = {
        "key_func": get_remote_address,
        "default_limits": [settings.RATE_LIMIT_DEFAULT],
    }
    if settings.CACHE_ENABLED:
        kwargs["storage_uri"] = settings.REDIS_URL
    return Limiter(**kwargs)


limiter = get_limiter()
