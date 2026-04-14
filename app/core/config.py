from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.scaling import apply_tier_defaults


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_ENV: str = "development"
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite+aiosqlite:///dev.db"
    SECRET_KEY: str = "change-me-to-a-random-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_EXPIRE_MINUTES: int = 15
    TOKEN_REVOCATION_ENABLED: bool = True

    APP_TITLE: str = "FastAPI Production Starter"
    APP_DESCRIPTION: str = "A production-ready FastAPI starter template."
    APP_VERSION: str = "0.1.0"

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: list[str] = ["Authorization", "Content-Type"]
    CORS_MAX_AGE: int = 600
    TRUSTED_HOSTS: list[str] = ["*"]

    AUTO_CREATE_TABLES: bool = True
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_READ_REPLICA_URL: str | None = None

    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_ENABLED: bool = False
    CACHE_DEFAULT_TTL: int = 300

    CELERY_BROKER_URL: str = "amqp://guest:guest@localhost:5672//"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_ENABLED: bool = False

    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = "noreply@example.com"
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    MAIL_ENABLED: bool = False
    FRONTEND_URL: str = "http://localhost:3000"

    SCALE_TIER: str = "basic"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return apply_tier_defaults(Settings())
