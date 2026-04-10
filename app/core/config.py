from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    APP_TITLE: str = "FastAPI Production Starter"
    APP_DESCRIPTION: str = "A production-ready FastAPI starter template."
    APP_VERSION: str = "0.1.0"

    CORS_ORIGINS: list[str] = ["*"]

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
