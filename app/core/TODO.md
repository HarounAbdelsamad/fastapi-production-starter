# TODO - `app/core/`

Core contains shared infrastructure (config, auth, middleware, logging, cache, helpers).

## Add in this folder when
- The code is reusable across multiple routers/services.
- The code is cross-cutting (security, observability, platform behavior).

## Typical additions
- New middleware (`middleware.py`) for request/response concerns.
- New dependency helpers used by many routes.
- New integrations (Sentry, metrics, external clients).

## Guidelines
- Prefer pure, testable functions.
- Read settings only through `get_settings()`.
- Avoid endpoint-specific logic here; keep that in routers/services.
