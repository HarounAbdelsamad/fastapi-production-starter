from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings


def apply_tier_defaults(settings: "Settings") -> "Settings":
    tier = settings.SCALE_TIER.lower()

    if tier == "standard":
        settings.CACHE_ENABLED = True
        settings.RATE_LIMIT_ENABLED = True
        settings.METRICS_ENABLED = True
        settings.DB_POOL_SIZE = max(settings.DB_POOL_SIZE, 20)
        settings.DB_MAX_OVERFLOW = max(settings.DB_MAX_OVERFLOW, 20)
    elif tier == "advanced":
        settings.CACHE_ENABLED = True
        settings.CELERY_ENABLED = True
        settings.RATE_LIMIT_ENABLED = True
        settings.METRICS_ENABLED = True
        settings.FEATURE_FLAGS_ENABLED = True
        settings.WEBSOCKET_ENABLED = True
        settings.DB_POOL_SIZE = max(settings.DB_POOL_SIZE, 50)
        settings.DB_MAX_OVERFLOW = max(settings.DB_MAX_OVERFLOW, 50)
    elif tier == "enterprise":
        settings.CACHE_ENABLED = True
        settings.CELERY_ENABLED = True
        settings.RATE_LIMIT_ENABLED = True
        settings.METRICS_ENABLED = True
        settings.FEATURE_FLAGS_ENABLED = True
        settings.WEBSOCKET_ENABLED = True
        settings.LOG_FORMAT = "json"
        settings.DB_POOL_SIZE = max(settings.DB_POOL_SIZE, 100)
        settings.DB_MAX_OVERFLOW = max(settings.DB_MAX_OVERFLOW, 100)

    return settings
