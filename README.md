# FastAPI Production Starter

A batteries-included, production-ready **FastAPI** template built for learning and shipping real backends fast.

![CI](https://github.com/<your-username>/fastapi-production-starter/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.13%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **Async everything** — SQLAlchemy 2.0 async engine + sessions
- **Pydantic v2 settings** — typed config from `.env`, zero guessing
- **Structured logging** — consistent format, quiet in prod, verbose in debug
- **CORS middleware** — configured out of the box
- **Global exception handler** — no raw tracebacks leaking to clients
- **Health check endpoint** — `GET /health` ready for load balancers
- **Auto table creation** — tables created on first request (swap for Alembic later)
- **PBKDF2 password hashing** — stdlib only, no native dependency headaches
- **Async test suite** — pytest + httpx + pytest-asyncio with in-memory SQLite
- **CI pipeline** — GitHub Actions with ruff lint + pytest
- **uv package manager** — fast, reproducible installs

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
│   │   └── security.py       # Password hashing & verification
│   ├── db/
│   │   └── database.py       # Async engine, session, Base, init_db
│   ├── models/
│   │   └── user.py           # SQLAlchemy ORM model
│   ├── schemas/
│   │   └── user.py           # Pydantic request/response schemas
│   ├── services/
│   │   └── user_service.py   # Business logic layer
│   ├── routers/
│   │   ├── health.py         # GET /health
│   │   ├── user.py           # CRUD /api/users
│   │   └── headers.py        # Header echo utility
│   └── internal/
│       └── admin.py          # Admin placeholder
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
| `POST`   | `/api/users/`     | Create a user      |
| `GET`    | `/api/users/`     | List all users     |
| `GET`    | `/api/users/{id}` | Get user by ID     |
| `PATCH`  | `/api/users/{id}` | Update user        |
| `DELETE` | `/api/users/{id}` | Delete user        |

---

## Configuration

All config lives in `.env` and is validated by Pydantic on startup. See `.env.example` for all available options.

| Variable        | Default                          | Description                    |
|-----------------|----------------------------------|--------------------------------|
| `DATABASE_URL`  | `sqlite+aiosqlite:///dev.db`     | Async DB connection string     |
| `SECRET_KEY`    | `change-me-to-a-random-secret`   | Signing key for tokens/cookies |
| `APP_ENV`       | `development`                    | `development` / `production`   |
| `DEBUG`         | `false`                          | Verbose logging + SQL echo     |
| `CORS_ORIGINS`  | `["*"]`                          | Allowed CORS origins           |

---

## Roadmap

- [ ] JWT authentication & protected routes
- [ ] Alembic database migrations
- [ ] Dockerfile & docker-compose
- [ ] Role-based access control
- [ ] Rate limiting middleware
- [ ] Pagination helpers

---

## License

[MIT](LICENSE)
