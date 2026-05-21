# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased]

---

## [0.1.0] - 2026-05-20

### Phase 9 — Launch preparation

#### Added
- `README.md` rewritten: updated roadmap (all v0.1 items complete), Operations feature
  table updated with idempotency/circuit breakers/webhooks, GitHub Pages docs badge
- `CHANGELOG.md` — this file, covering all phases
- `cookiecutter.json` — Cookiecutter template parameters for `cookiecutter gh:HarounAbdelsamad/fastapi-production-starter`
- `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1
- `examples/project-tracker/` — reference implementation demonstrating multi-tenant
  RBAC + audit log + webhooks + OTel + feature flags + background jobs

### Phase 8 — OWASP hardening + packaging

#### Added
- `SECURITY.md` — vulnerability reporting process, OWASP Top-10 coverage table,
  production hardening checklist
- `.github/workflows/docker.yml` — multi-arch Docker build (linux/amd64 + linux/arm64)
  pushed to GHCR on semver tags; build attestation via `attest-build-provenance`
- `app/core/config.py` — `IDEMPOTENCY_TTL`, `SHUTDOWN_GRACE_SECONDS`,
  `JOB_QUEUE_BACKEND`, `WEBHOOKS_ENABLED` settings

### Phase 7 — Documentation site

#### Added
- `mkdocs.yml` — MkDocs Material theme; light/dark toggle; Mermaid diagram support;
  full navigation covering all 40+ doc pages
- `docs/index.md` — docs site home with feature table and quickstart
- `docs/getting-started.md` — install, first request, Docker stack, env var table
- `docs/recipes.md` — how-to walkthroughs: new entity, role, migration, OAuth provider,
  IdP, dependency, feature flag, PII tagging, webhook event, background task
- `docs/faq.md` — answers for General, Database, Auth, Observability, Compliance,
  Operations, and Development questions
- `.github/workflows/docs.yml` — GitHub Pages deployment triggered on push to
  `docs/**` or `mkdocs.yml`
- `pyproject.toml` — `[project.optional-dependencies] docs` group:
  `mkdocs-material>=9.5.0`

### Phase 6 — Operational patterns

#### Added
- `app/core/jobs.py` — `JobQueue` protocol + `CeleryJobQueue` adapter +
  `RQJobQueue` template; `get_job_queue()` factory respects `CELERY_ENABLED`
- `app/core/circuit_breaker.py` — async three-state circuit breaker
  (CLOSED → OPEN → HALF-OPEN) with `asyncio.Lock`, configurable threshold/timeout/
  half-open probe limit; usable as context manager or via `.call()`
- `app/core/idempotency.py` — `IdempotencyMiddleware` (Starlette `BaseHTTPMiddleware`);
  caches POST/PATCH responses by `Idempotency-Key` header; Redis store
  (when `CACHE_ENABLED`) with in-process dict fallback; replays add
  `X-Idempotent-Replayed: true` header
- `app/models/webhook.py` — `WebhookEndpoint` + `WebhookDelivery` models
- `app/services/webhook_service.py` — HMAC-SHA256 signing (`X-Webhook-Signature`),
  event matching, exponential backoff retry (30 s → 2 m → 8 m → 32 m → failed),
  `dispatch_event()`, `replay_delivery()`
- `app/routers/webhooks.py` — 5 admin-only endpoints: register, list, delete,
  delivery log, replay
- `app/models/feature_flag.py` — `FeatureFlagOverride` model
  (`key` + `subject_type` + `subject_id` unique constraint)
- Feature flag priority chain in `app/services/feature_service.py`:
  user override → tenant override → global flag; Redis cache with 60 s TTL
- Override management endpoints in `app/routers/features.py`:
  `PUT` and `DELETE /api/v1/admin/features/{key}/overrides/{subject_type}/{subject_id}`
- Graceful shutdown improvement in `app/main.py` — `SHUTDOWN_GRACE_SECONDS` respected
  in lifespan shutdown path; structured log on shutdown start/complete
- `tests/test_jobs.py` (5 tests), `tests/test_circuit_breaker.py` (12 tests),
  `tests/test_idempotency.py` (6 tests), `tests/test_webhooks.py` (14 tests),
  `tests/test_feature_flags_enhanced.py` (9 tests)
- `docs/operations/` — six new operation guides: background-jobs, webhooks,
  idempotency, circuit-breakers, graceful-shutdown, feature-flags

### Phase 5 — Compliance & GDPR

#### Added
- `app/core/gdpr.py` — `@mark_pii()` decorator, `pseudonymize_user()`,
  `delete_user_data()`; GDPR data-export endpoint
- `app/core/audit.py` — `log_event()` + `verify_audit_log()`; HMAC-SHA256
  per-row signature in `audit_logs.hmac_signature`; `LOG_PII_REDACT` filter
- `app/models/audit_log.py` — `AuditLog` model (append-only)
- `app/routers/admin.py` — `GET /api/v1/admin/audit-logs` export endpoint
- `docs/compliance/audit-log.md`, `docs/compliance/gdpr.md`

### Phase 4 — Identity & Secrets

#### Added
- `app/core/saml.py` — SAML 2.0 SP flows (SP-initiated); `python3-saml` backend
- `app/routers/saml.py` — `/auth/saml/login`, `/auth/saml/acs`,
  `/auth/saml/metadata`
- `app/core/apikey.py` — API key issue / rotate / revoke; `X-API-Key` header auth
- `app/routers/apikeys.py` — CRUD for API keys
- `app/core/secrets.py` — `SecretsProvider` protocol + `EnvSecretsProvider` (default),
  `VaultSecretsProvider`, `AWSSecretsManagerProvider` skeletons
- `app/core/config.py` — `SECRETS_BACKEND`, `VAULT_*`, `AWS_SECRET_ID` settings
- `docs/adr/004-pluggable-secrets.md`, `docs/adr/006-saml-library.md`

### Phase 3 — Multi-tenancy & RBAC

#### Added
- `app/models/tenant.py` — `Tenant` model; `TenantMixin` for row-level isolation
- `app/core/rbac.py` — `require_role()` dependency; `Permission` enum; role hierarchy
- `app/routers/admin.py` — admin dashboard endpoint
- `app/services/feature_service.py` — feature flag CRUD + evaluation
- `app/models/feature_flag.py` — `FeatureFlag` model
- `app/routers/features.py` — admin feature flag endpoints
- `docs/adr/005-multi-tenancy.md`

### Phase 2 — Production hardening baseline

#### Added
- Rate limiting middleware (`slowapi`); `RATE_LIMIT_ENABLED` toggle
- `RequestIDMiddleware` — injects `X-Request-ID` on every response
- `SecurityHeadersMiddleware` — CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- Error envelope: all 4xx/5xx responses use `{"error": {...}}` JSON structure
- API versioning under `/api/v1`
- Deep health probes: `/health/live`, `/health/ready`, `/health/dependencies`
- Prometheus metrics endpoint (`METRICS_ENABLED`); Sentry integration (`SENTRY_DSN`)
- Login throttle (`LOGIN_MAX_ATTEMPTS`, `LOGIN_LOCKOUT_SECONDS`)
- File upload endpoint (`STORAGE_BACKEND=local|s3`); `FILE_MAX_SIZE_MB`
- Soft-delete mixin (`deleted_at` column)
- `app/cli.py` — `create-admin`, `seed`, `generate-secret`, `check-config` commands
- WebSocket scaffold (`WEBSOCKET_ENABLED`)
- OAuth 2.0 adapters: Google, GitHub (`OAUTH_*_ENABLED`)
- `app/core/scaling.py` — `SCALE_TIER` presets (basic / standard / enterprise)
- `docs/adr/007-opentelemetry-default.md` through `docs/adr/012-versioning-compatibility.md`

### Phase 1 — Starter foundation

#### Added
- FastAPI application with async SQLAlchemy 2.0 (`AsyncSession`), Alembic migrations
- JWT access + refresh token auth; `RevokedToken` model (`TOKEN_REVOCATION_ENABLED`)
- Password reset flow
- RBAC scaffolding (User, Role models)
- Pagination helpers
- Redis + Celery + Docker Compose stack
- CI workflow (lint + test; Postgres / MySQL / SQLite matrix)
- `docs/adr/001-why-fastapi.md` through `docs/adr/003-multi-db-support.md`
- `docs/architecture/overview.md`
