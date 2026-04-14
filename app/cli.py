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


if __name__ == "__main__":
    app()
