# Contributing

## Getting Started
- Fork and clone the repository.
- Run `make install`.
- Run `make pre-commit-install`.

## Development Workflow
- Use branch prefixes: `feature/`, `fix/`, `docs/`, `chore/`.
- Keep commits focused and descriptive.
- Before push: `make lint && make test`.

## Pull Request Process
- Include a clear summary and test notes.
- Link related issue(s).
- Ensure CI is green.

## Code Style
- Ruff is the source of truth for linting/formatting.
- Add type hints for public functions.
- Avoid `Any` unless truly required.

## Testing
- Place tests under `tests/`.
- Prefer async integration tests for API behavior.
- Maintain at least 70% application coverage.

## Architecture
- Keep separation of concerns: `core`, `db`, `models`, `schemas`, `services`, `routers`.
- Business logic belongs in `services`, not routers.

## Where code goes

`app/` is the backend source root. For a new feature:

1. Define request and response contracts in `app/schemas/`.
2. Add persistence entities in `app/models/` if needed, and export them from `app/models/__init__.py`.
3. Implement business logic in `app/services/`.
4. Expose HTTP endpoints in `app/routers/`.
5. Wire cross-cutting concerns in `app/core/`.
6. Register the router in `app/main.py`.
7. Add tests in `tests/`.

Keep routers thin. Read settings only through `get_settings()`. Put security checks in dependencies and middleware, not duplicated in handlers. Keep all configuration in `app/core/config.py` and `.env`.

### `app/schemas/`
Pydantic request and response contracts. Use names like `<Entity>Create`, `<Entity>Update`, and `<Entity>Response`. Set `ConfigDict(from_attributes=True)` on ORM-backed responses. Never return ORM objects directly from endpoints.

### `app/models/`
SQLAlchemy entities. Inherit from `Base` and the mixins you need. Models describe data shape and light behavior; heavy rules stay in services. After a model change, add an Alembic revision. Do not edit a migration that has already been applied in a shared environment.

### `app/services/`
Business logic and database operations. Services should be framework-light and easy to test. Do not set HTTP status codes or format responses here.

### `app/routers/`
HTTP endpoints. Create `router = APIRouter()`, keep handlers thin, and take auth through `Depends(...)`. Use versioned paths (`/api/v1/...`). Cover each route's success path and its failure modes in tests.

### `app/core/`
Shared infrastructure: config, auth, middleware, logging, cache, and other cross-cutting code. Prefer pure, testable functions. Do not put endpoint-specific logic here.

### `app/db/`
Engine, session, mixins, and tenant filters. Keep initialization lazy and environment-safe. Do not embed business logic in DB helpers. Remember SQLite and the other supported engines.

### `app/events/`
Domain event handlers. Emit with `emit("event.name", ...)` and register with `@on("event.name")`. Handlers should be idempotent and limited to side effects (email, audit, cache). Do not put core business decisions in handlers.

### `app/internal/`
Admin and maintenance endpoints that are not public product APIs. Protect every route with `require_role("admin")` or stronger. Never expose an internal route without authentication and authorization.

### `app/tasks/`
Celery tasks. Decorate with `@celery_app.task(name="tasks.your_task_name")`, keep payloads JSON-serializable, and make tasks safe for retries and duplicate delivery.

### `app/templates/`
Email and other rendered assets, grouped by domain (`email/`, and similar). Reference a template from the sender (`send_email(..., template_name="...")`) and pass every variable through `context`. Keep markup simple. Never hardcode secrets in a template.

### `alembic/`
Schema migrations.

1. Update the SQLAlchemy models.
2. Run `uv run alembic revision --autogenerate -m "your message"`.
3. Review the generated file: indexes, nullability, defaults, and any data migration.
4. Run `uv run alembic upgrade head`.

One coherent schema change per revision when you can, with a safe downgrade. `alembic/templates/` holds starter env files per database engine; keep those minimal.

### `tests/`
Mirror production modules with `test_<module>.py`. Cover the success path, validation failures, and auth failures. Use fixtures from `conftest.py` and keep tests isolated.

### `docs/`
Document new deploy and runtime behavior, environment variables, toggles, and setup workflows. Keep the docs aligned with the actual code paths and command names.

### `.github/`
CI workflows, issue and PR templates, and Dependabot config. Keep checks fast enough for contributors and strict enough to gate quality. Name jobs and outputs so a failing run is easy to debug.
