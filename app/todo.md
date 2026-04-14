# TODO - `app/`

Use this folder as the backend source root.

## When adding a new feature
1. Define request/response contracts in `schemas/`.
2. Add persistence entities in `models/` (if needed).
3. Implement business logic in `services/`.
4. Expose HTTP endpoints in `routers/`.
5. Wire cross-cutting concerns in `core/`.
6. Register routers in `app/main.py`.
7. Add tests in `tests/`.

## Rules
- Keep routers thin and move logic to services.
- Keep all configuration in `core/config.py` + `.env`.
- Keep security checks in dependencies/middleware (not duplicated in handlers).
