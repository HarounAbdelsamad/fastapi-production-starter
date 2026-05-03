import asyncio
import secrets
from uuid import uuid4

import typer

from app.db.database import SessionLocal, init_db
from app.schemas.user import UserCreate
from app.services.user_service import create_user

app = typer.Typer()


async def _create_admin(username: str, email: str, password: str) -> None:
    await init_db()
    async with SessionLocal() as db:
        user = await create_user(
            db,
            UserCreate(
                user_id=f"admin-{uuid4().hex[:8]}",
                username=username,
                password=password,
                email=email,
                phone_number=None,
                role="admin",
            ),
        )
        if user is None:
            raise typer.BadParameter("Admin could not be created (duplicate data).")


@app.command()
def create_admin(username: str, email: str, password: str) -> None:
    asyncio.run(_create_admin(username, email, password))
    typer.echo("Admin created.")


@app.command()
def seed() -> None:
    asyncio.run(_create_admin("admin", "admin@example.com", "change-me-admin-pass"))
    typer.echo("Seeded base data.")


@app.command()
def generate_secret() -> None:
    typer.echo(secrets.token_urlsafe(64))


@app.command("check-config")
def check_config(
    env_file: str = typer.Option(".env", help="Path to .env file to validate"),
    strict: bool = typer.Option(False, "--strict", help="Exit 1 on warnings, not just errors"),
) -> None:
    """Validate configuration for the current environment.

    Checks that all required keys are present for each active feature toggle
    and that production-critical settings meet the minimum bar.

    Exit codes:
        0 — configuration is valid
        1 — one or more errors (or warnings with --strict)
    """
    import os

    from dotenv import load_dotenv

    # Load the target env file so we validate what would actually run.
    if os.path.exists(env_file):
        load_dotenv(env_file, override=True)
    else:
        typer.echo(f"Warning: env file '{env_file}' not found — validating current environment")

    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()

    typer.echo(
        f"Checking configuration (APP_ENV={settings.APP_ENV}, SCALE_TIER={settings.SCALE_TIER})"
    )

    errors = settings.validate_config()

    # Additional informational warnings (non-fatal)
    warnings: list[str] = []
    if settings.is_development and settings.DATABASE_URL == "sqlite+aiosqlite:///dev.db":
        warnings.append(
            "DATABASE_URL is the default SQLite dev database — change for staging/production"
        )
    if settings.CACHE_ENABLED and settings.REDIS_URL == "redis://localhost:6379/0":
        warnings.append("REDIS_URL is the default localhost value — ensure Redis is reachable")
    if settings.METRICS_ENABLED:
        typer.echo("  INFO: METRICS_ENABLED=true — /metrics endpoint will be exposed")
    if settings.OTLP_ENDPOINT:
        typer.echo(f"  INFO: Traces will be exported to {settings.OTLP_ENDPOINT}")
    if settings.SECRETS_BACKEND != "env":
        typer.echo(f"  INFO: SECRETS_BACKEND={settings.SECRETS_BACKEND}")

    has_issues = False

    for warning in warnings:
        typer.echo(f"  WARN: {warning}", err=False)
        if strict:
            has_issues = True

    for error in errors:
        typer.echo(f"  ERROR: {error}", err=True)
        has_issues = True

    if has_issues:
        typer.echo("\nConfiguration check FAILED", err=True)
        raise typer.Exit(1)
    else:
        typer.echo(f"\nConfiguration OK ({len(warnings)} warning(s), 0 errors)")


if __name__ == "__main__":
    app()
