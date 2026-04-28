# FastAPI Production Starter

Template-grade FastAPI backend with enterprise-ready patterns and feature toggles.

![CI](https://github.com/HarounAbdelsamad/fastapi-production-starter/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.13%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Why this template
- Clean architecture (`core`, `db`, `models`, `schemas`, `services`, `routers`)
- Versioned API under `/api/v1`
- Toggle-able features via `.env` (cache, celery, metrics, sentry, websockets, feature flags, oauth, uploads)
- Security baseline: request IDs, security headers, rate limits, auth throttling, audit logs

## Quick start
```bash
git clone https://github.com/HarounAbdelsamad/fastapi-production-starter.git
cd fastapi-production-starter
make install
cp .env.example .env
make run
```

Open docs at `http://127.0.0.1:8000/docs`.

## Core endpoints
- `GET /health`, `GET /health/live`, `GET /health/ready`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/password-reset/request`
- `POST /api/v1/auth/password-reset/confirm`
- `GET|POST|PATCH|DELETE /api/v1/users/...`
- `GET /api/v1/admin/dashboard`
- `GET /api/v1/admin/audit-logs`
- `GET|PUT /api/v1/admin/features...`
- `POST /api/v1/files/upload`
- `DELETE /api/v1/files/{path}`

## Toggle-able features
| Feature | Env key | Default |
|---|---|---|
| Rate limiting | `RATE_LIMIT_ENABLED` | `false` |
| Redis cache | `CACHE_ENABLED` | `false` |
| Celery queues | `CELERY_ENABLED` | `false` |
| Metrics | `METRICS_ENABLED` | `false` |
| Sentry | `SENTRY_DSN` | empty |
| WebSocket | `WEBSOCKET_ENABLED` | `false` |
| Feature flags | `FEATURE_FLAGS_ENABLED` | `false` |
| OAuth providers | `OAUTH_*` | empty |
| Storage backend | `STORAGE_BACKEND` | `local` |

## CLI commands
- `uv run cli generate-secret`
- `uv run cli seed`
- `uv run cli create-admin --username admin --email admin@example.com --password supersecret`

## Developer workflow
- Lint: `make lint`
- Format check: `make format-check`
- Test: `make test`
- Coverage: `make test-cov`
- Migrate: `make migrate`
- Docker stack: `make docker-up`

## Docs
- Deployment: `docs/deployment.md`
- OAuth setup: `docs/oauth.md`
- Multi-tenancy pattern: `docs/multi-tenancy.md`
- Contributing: `CONTRIBUTING.md`
- Changelog: `CHANGELOG.md`

## License
[MIT](LICENSE)
