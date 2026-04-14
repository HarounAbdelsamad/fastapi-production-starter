# TODO - `alembic/`

Migration tooling and environment setup live here.

## How to create a migration
1. Update SQLAlchemy models.
2. Run: `uv run alembic revision --autogenerate -m "your message"`.
3. Review generated migration manually.
4. Run: `uv run alembic upgrade head`.

## Rule
- Never rely on autogenerate blindly; verify indexes, nullability, defaults, and data migrations.
