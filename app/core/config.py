from __future__ import annotations

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
    LOG_FORMAT: str = "text"

    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_AUTH: str = "10/minute"

    METRICS_ENABLED: bool = False
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_SECONDS: int = 300
    API_KEYS: list[str] = []

    STORAGE_BACKEND: str = "local"
    STORAGE_LOCAL_PATH: str = "./uploads"
    S3_BUCKET_NAME: str = ""
    S3_REGION: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_ENDPOINT_URL: str = ""

    WEBSOCKET_ENABLED: bool = False
    FEATURE_FLAGS_ENABLED: bool = False

    OAUTH_GOOGLE_CLIENT_ID: str = ""
    OAUTH_GOOGLE_CLIENT_SECRET: str = ""
    OAUTH_GITHUB_CLIENT_ID: str = ""
    OAUTH_GITHUB_CLIENT_SECRET: str = ""

    # -- Secrets backend (see docs/adr/004-pluggable-secrets.md) ------------
    # Valid values: "env" (default), "vault", "aws"
    SECRETS_BACKEND: str = "env"
    # Vault-specific (only read when SECRETS_BACKEND=vault)
    VAULT_ADDR: str = "http://localhost:8200"
    VAULT_TOKEN: str = ""
    VAULT_MOUNT: str = "secret"
    VAULT_PATH: str = "app"
    # AWS-specific (only read when SECRETS_BACKEND=aws)
    AWS_SECRET_ID: str = ""
    AWS_REGION: str = ""

    # -- OpenTelemetry (see docs/adr/007-opentelemetry-default.md) -----------
    # Set to an OTLP endpoint (e.g. "http://jaeger:4317") to export traces.
    # Leave empty to use the noop exporter (zero overhead).
    OTLP_ENDPOINT: str = ""
    # Set to "true" to disable the OTel SDK entirely (removes all overhead).
    OTEL_SDK_DISABLED: bool = False
    # Fraction of traces to sample (1.0 = 100%, 0.1 = 10%). Uses ParentBased sampler.
    OTEL_SAMPLE_RATE: float = 1.0
    # Set to "true" to redact PII patterns (email, phone, credit card) from logs.
    LOG_PII_REDACT: bool = False

    # -- SAML 2.0 (see docs/identity/saml-setup.md) -------------------------
    # Install python3-saml to enable: uv pip install 'python3-saml>=1.16.0'
    SAML_ENABLED: bool = False
    BASE_URL: str = "http://localhost:8000"
    SAML_IDP_ENTITY_ID: str = ""
    SAML_IDP_SSO_URL: str = ""
    SAML_IDP_SLO_URL: str = ""
    SAML_IDP_CERT: str = ""
    SAML_SP_CERT: str = ""
    SAML_SP_KEY: str = ""

    # -- Service-to-service auth (see docs/identity/s2s-auth.md) ------------
    # S2S_SERVICES is a JSON object mapping service IDs to shared secrets.
    # Example: {"analytics-service": "mysecret", "worker": "anothersecret"}
    S2S_ENABLED: bool = False
    S2S_SERVICES: str = "{}"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_testing(self) -> bool:
        return self.APP_ENV == "testing"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    def validate_config(self) -> list[str]:
        """Return a list of configuration error strings.

        Called by ``make check-config`` and at startup in production.
        Returns an empty list when the configuration is valid.
        """
        errors: list[str] = []

        if self.is_production:
            if self.SECRET_KEY in ("change-me-to-a-random-secret", ""):
                errors.append("SECRET_KEY must be set to a strong random value in production")
            if len(self.SECRET_KEY) < 64:
                errors.append(
                    f"SECRET_KEY is too short ({len(self.SECRET_KEY)} chars); "
                    "minimum 64 characters required in production"
                )

        if self.CACHE_ENABLED and not self.REDIS_URL:
            errors.append("REDIS_URL is required when CACHE_ENABLED=true")

        if self.CELERY_ENABLED:
            if not self.CELERY_BROKER_URL:
                errors.append("CELERY_BROKER_URL is required when CELERY_ENABLED=true")
            if not self.CELERY_RESULT_BACKEND:
                errors.append("CELERY_RESULT_BACKEND is required when CELERY_ENABLED=true")

        if self.STORAGE_BACKEND == "s3":
            for key in ("S3_BUCKET_NAME", "S3_REGION", "S3_ACCESS_KEY", "S3_SECRET_KEY"):
                if not getattr(self, key):
                    errors.append(f"{key} is required when STORAGE_BACKEND=s3")

        if self.MAIL_ENABLED:
            for key in ("MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_SERVER"):
                if not getattr(self, key):
                    errors.append(f"{key} is required when MAIL_ENABLED=true")

        if self.OAUTH_GOOGLE_CLIENT_ID and not self.OAUTH_GOOGLE_CLIENT_SECRET:
            errors.append(
                "OAUTH_GOOGLE_CLIENT_SECRET is required when OAUTH_GOOGLE_CLIENT_ID is set"
            )
        if self.OAUTH_GITHUB_CLIENT_ID and not self.OAUTH_GITHUB_CLIENT_SECRET:
            errors.append(
                "OAUTH_GITHUB_CLIENT_SECRET is required when OAUTH_GITHUB_CLIENT_ID is set"
            )

        if self.SECRETS_BACKEND == "vault" and not self.VAULT_TOKEN:
            errors.append(
                "VAULT_TOKEN is required when SECRETS_BACKEND=vault "
                "(or configure AppRole auth manually)"
            )
        if self.SECRETS_BACKEND == "aws" and not self.AWS_SECRET_ID:
            errors.append("AWS_SECRET_ID is required when SECRETS_BACKEND=aws")

        return errors


@lru_cache
def get_settings() -> Settings:
    return apply_tier_defaults(Settings())
