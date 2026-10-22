# Deployment Guide

## 1) Local Development

```bash
uv sync --extra dev
copy .env.example .env
uv run uvicorn app.main:app --reload
```

## 2) Docker

Published multi-arch image (linux/amd64 and linux/arm64), built when a version tag is pushed:

```bash
docker run --rm -p 8000:8000 \
  -e PORT=8000 \
  ghcr.io/harounabdelsamad/fastapi-production-starter:0.1.1
```

The process listens on `0.0.0.0:$PORT` and serves `/health/live`. Set `SECRET_KEY` (64+ characters) before `APP_ENV=production`.

Compose, for local Postgres, Redis, and the worker:

```bash
docker compose up -d --build
```

Health check:

```bash
curl http://localhost:8000/health
```

## 3) VM Deployment (Ubuntu)

1. Install Python 3.13 and uv.
2. Clone repo and configure `.env`.
3. Run migrations:
   ```bash
   uv run alembic upgrade head
   ```
4. Start app with systemd:
   - service command: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`
5. Put Nginx in front and terminate TLS with Certbot.

## 4) Managed Platforms (Render/Railway/Fly)

- Set environment variables from `.env.example`.
- Use start command:
  ```bash
  uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
- Point `DATABASE_URL`, `REDIS_URL`, and `CELERY_BROKER_URL` to managed services.

## 5) Kubernetes (High Scale)

- Use ConfigMap for non-secret values.
- Use Secret for sensitive env vars (`SECRET_KEY`, DB creds, mail creds).
- Run migrations in an init container before app starts.
- Add HPA for autoscaling.

## 6) CI/CD

Current GitHub workflow runs:
1. Ruff lint + format check
2. Pytest

Recommended extension:
- Build image
- Push image to registry
- Deploy on tag/release
