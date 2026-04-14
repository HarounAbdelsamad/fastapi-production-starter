# FastAPI Production Starter

A batteries-included, production-ready **FastAPI** template built for learning and shipping real backends fast.

![CI](https://github.com/<your-username>/fastapi-production-starter/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.13%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **JWT auth + OAuth2 password flow** with access/refresh tokens
- **Refresh rotation and token revocation store** (`revoked_tokens`)
- **Password reset endpoints** + email service integration (`fastapi-mail`)
- **RBAC-ready users** with role checks and protected admin endpoints
- **Alembic async migrations** + backend templates (SQLite/Postgres/MySQL/MariaDB + Mongo guide)
- **Pagination primitives** (`PaginationParams`, `PaginatedResponse`)
- **Redis cache layer** and invalidation helpers (config gated)
- **Celery + RabbitMQ integration** for background workloads (config gated)
- **FastAPI background tasks abstraction** for lightweight async jobs
- **Adaptive scale tiers** (`basic`, `standard`, `advanced`, `enterprise`)
- **Docker + docker compose stack** with Postgres, Redis, RabbitMQ, Celery worker/beat
- **Deployment guide** at `docs/deployment.md`

---

## Project Structure

```
.
├── app/
│   ├── main.py              # App factory, lifespan, middleware
│   ├── core/
│   │   ├── config.py         # Pydantic settings (reads .env)
│   │   ├── exceptions.py     # Global exception handler
│   │   ├── logging.py        # Logging setup
│   │   ├── auth.py           # JWT encode/decode helpers
│   │   ├── cache.py          # Redis cache client and helpers
│   │   ├── deps.py           # current-user dependency
│   │   ├── email.py          # mail sender wrapper
│   │   ├── pagination.py     # generic pagination helper
│   │   ├── permissions.py    # role-based dependency
│   │   ├── scaling.py        # adaptive tier defaults
│   │   └── security.py       # Password hashing & verification
│   ├── db/
│   │   └── database.py       # Async engine, session, Base, init_db
│   ├── models/
│   │   ├── revoked_token.py  # Revoked token persistence
│   │   └── user.py           # SQLAlchemy ORM model
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── pagination.py
│   │   ├── password.py
│   │   └── user.py
│   ├── services/
│   │   └── user_service.py   # Business logic layer
│   ├── routers/
│   │   ├── auth.py           # Auth endpoints
│   │   ├── health.py         # GET /health
│   │   ├── user.py           # CRUD /api/users
│   │   └── headers.py        # Header echo utility
│   └── internal/
│       └── admin.py          # Admin placeholder
├── alembic/                  # Async migration config and versions
├── docs/deployment.md
├── docker-compose.yml
├── Dockerfile
├── tests/
│   ├── conftest.py           # Fixtures (async client, DB)
│   ├── test_health.py
│   └── test_users.py
├── .env.example
├── .github/workflows/ci.yml
├── pyproject.toml
├── LICENSE
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

```bash
# Clone
git clone https://github.com/<your-username>/fastapi-production-starter.git
cd fastapi-production-starter

# Install dependencies
uv sync --extra dev

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run the server
uv run uvicorn app.main:app --reload

# Open docs
# http://127.0.0.1:8000/docs
```

### Run Tests

```bash
uv run pytest -v
```

### Lint

```bash
uv run ruff check .
uv run ruff format --check .
```

---

## API Endpoints

| Method   | Path              | Description        |
|----------|-------------------|--------------------|
| `GET`    | `/health`         | Health check       |
| `POST`   | `/api/auth/login` | Login and issue JWT tokens |
| `POST`   | `/api/auth/refresh` | Rotate refresh token pair |
| `POST`   | `/api/auth/logout` | Revoke current access/refresh tokens |
| `POST`   | `/api/auth/password-reset/request` | Request reset email |
| `POST`   | `/api/auth/password-reset/confirm` | Confirm reset token |
| `POST`   | `/api/users/`     | Create a user      |
| `GET`    | `/api/users/`     | List users (paginated) |
| `GET`    | `/api/users/{id}` | Get user by ID     |
| `PATCH`  | `/api/users/{id}` | Update user        |
| `DELETE` | `/api/users/{id}` | Delete user        |

---

## Configuration

All config lives in `.env` and is validated by Pydantic on startup. See `.env.example` for all available options.

| Variable        | Default                          | Description                    |
|-----------------|----------------------------------|--------------------------------|
| `DATABASE_URL`  | `sqlite+aiosqlite:///dev.db`     | Async DB connection string     |
| `SECRET_KEY`    | `change-me-to-a-random-secret`   | JWT signing key                |
| `SCALE_TIER`    | `basic`                          | `basic/standard/advanced/enterprise` |
| `AUTO_CREATE_TABLES` | `true`                      | Startup create-all toggle (useful for local) |
| `REDIS_URL`     | `redis://localhost:6379/0`       | Redis cache URL                |
| `CACHE_ENABLED` | `false`                          | Enable Redis caching           |
| `CELERY_BROKER_URL` | `amqp://guest:guest@localhost:5672//` | RabbitMQ broker URL |
| `CELERY_ENABLED`| `false`                          | Enable Celery workers          |
| `MAIL_ENABLED`  | `false`                          | Enable outbound SMTP           |

---

## Scale Tier Behavior

| Estimated Daily Requests | Tier | Backend behavior |
|---|---|---|
| `< 100,000` | `basic` | single instance, no Redis/Celery by default |
| `100,000 - 1,000,000` | `standard` | Redis cache enabled, larger DB pool |
| `1,000,000 - 10,000,000` | `advanced` | Redis + Celery enabled, high pool |
| `> 10,000,000` | `enterprise` | enterprise defaults (high pool, distributed ready) |

---

## License

[MIT](LICENSE)
