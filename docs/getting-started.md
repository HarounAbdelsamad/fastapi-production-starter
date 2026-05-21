# Getting Started

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker (for the full stack — optional for basic dev)

## Install

```bash
git clone https://github.com/HarounAbdelsamad/fastapi-production-starter.git
cd fastapi-production-starter
make install          # uv sync --extra dev
cp .env.example .env  # copy default config
```

## First request

```bash
make run
# → Uvicorn running on http://127.0.0.1:8000

# Liveness check
curl http://127.0.0.1:8000/health/live
# {"status":"ok"}

# OpenAPI docs (development only)
open http://127.0.0.1:8000/docs
```

## Create the first admin user

```bash
uv run cli create-admin
# → prompts for email + password
```

## Login and get a token

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin@example.com", "password": "your-password"}'
# → {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}
```

## Full observability stack (Docker)

```bash
docker compose up --profile observability
```

| Service | URL | Credentials |
|---|---|---|
| API | http://localhost:8000 | — |
| Jaeger (traces) | http://localhost:16686 | — |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |

To see traces: make a request, then open Jaeger and search for service
`FastAPI Production Starter`.

## SAML with Keycloak (optional)

```bash
docker compose up --profile saml
# Keycloak admin: http://localhost:8080  (admin / admin)
```

Then set `SAML_ENABLED=true` in `.env` and follow the
[SAML setup guide](identity/saml-setup.md).

## Environment variables

All settings live in `.env` (copied from `.env.example`).  The file is validated at
startup — run `make check-config` to validate without starting the server.

Key settings:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | SQLite `dev.db` | Switch to Postgres/MySQL for production |
| `SECRET_KEY` | `change-me` | JWT signing key — **change before deploy** |
| `CACHE_ENABLED` | `false` | Enable Redis-backed caching |
| `CELERY_ENABLED` | `false` | Enable background task queue |
| `RATE_LIMIT_ENABLED` | `false` | Enable per-IP rate limiting |
| `OTLP_ENDPOINT` | empty | Set to export OTel spans to Jaeger |

Generate a secure key:

```bash
uv run cli generate-secret
```

## Running tests

```bash
make test        # pytest with coverage (≥50% required)
make lint        # ruff check
make format-check
```

The CI matrix tests against SQLite, PostgreSQL, and MySQL in parallel.  To run against
Postgres locally:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/testdb uv run pytest
```

## Next steps

- [Architecture overview](architecture/overview.md) — understand how the layers fit together
- [Identity guide](identity/oauth.md) — add OAuth providers or SAML
- [Deployment guide](deployment.md) — Docker, Kubernetes, cloud platforms
- [Recipes](recipes.md) — how to add a new entity, role, migration, or IdP
