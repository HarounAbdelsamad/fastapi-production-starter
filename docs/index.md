# FastAPI Production Starter

> Enterprise FastAPI foundation.  
> SAML. Multi-DB. OpenTelemetry. Audit logs. Zero-downtime migrations.  
> All wired. All toggleable. Off by default.

[![CI](https://github.com/HarounAbdelsamad/fastapi-production-starter/actions/workflows/ci.yml/badge.svg)](https://github.com/HarounAbdelsamad/fastapi-production-starter/actions)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://github.com/HarounAbdelsamad/fastapi-production-starter/blob/master/LICENSE)

---

## What this is

A backend-only FastAPI foundation for enterprise teams.  Every feature that costs a week
to wire correctly is pre-wired — SAML SSO, row-level multi-tenancy, HMAC-signed audit
logs, OpenTelemetry distributed tracing, zero-downtime migration playbook — and
**toggled off by default** so you adopt at your own pace.

Twelve Architecture Decision Records explain every opinionated choice.

## Who it's for

- Backend leads at 50–500-person companies told to "pick our backend foundation"
- Platform teams building internal APIs on FastAPI
- Engineering consultancies standardising client project backends

**Not for:** full-stack starters, SaaS-in-a-box, tutorial projects, AI/ML apps.

## 60-second quickstart

```bash
git clone https://github.com/HarounAbdelsamad/fastapi-production-starter.git
cd fastapi-production-starter
make install
cp .env.example .env
make run
# API:  http://127.0.0.1:8000
# Docs: http://127.0.0.1:8000/docs
```

Full observability + identity stack (Docker required):

```bash
docker compose up --profile observability
# Jaeger:     http://localhost:16686
# Grafana:    http://localhost:3000  (admin / admin)
# Prometheus: http://localhost:9090
```

## Feature summary

| Area | Highlights |
|---|---|
| **Identity** | JWT + refresh, OAuth (Google/GitHub), SAML 2.0, API keys, RBAC with hierarchy, S2S auth |
| **Data** | Postgres / MySQL / SQLite CI-tested, async SQLAlchemy 2.0, Alembic, multi-tenancy, soft delete |
| **Observability** | OpenTelemetry SDK, Prometheus, Grafana dashboard, structured JSON logs, trace ID per log line |
| **Compliance** | HMAC-signed audit log, GDPR export/pseudonymize, PII field registry, security headers |
| **Operations** | Background jobs (Celery/RQ), outgoing webhooks, idempotency keys, circuit breakers, feature flags |

## Navigation

- **[Getting Started](getting-started.md)** — install, run, first request
- **[Architecture](architecture/overview.md)** — system diagram, layers, request lifecycle
- **[ADRs](architecture/decisions.md)** — 12 architecture decisions with rationale
- **[Identity](identity/oauth.md)** — auth flows, SAML, API keys, RBAC
- **[Compliance](compliance/audit-log.md)** — audit log, GDPR, PII tagging
- **[Operations](operations/background-jobs.md)** — jobs, webhooks, idempotency, circuit breakers
- **[Recipes](recipes.md)** — "how do I add X?" one-pagers
- **[FAQ](faq.md)** — common questions

## Reference implementation

A working multi-tenant project tracker built on top of this template demonstrates SAML
SSO, row-level tenancy, audit logging, and the full observability stack in a real
application context.

→ [`examples/project-tracker/`](https://github.com/HarounAbdelsamad/fastapi-production-starter/tree/master/examples/project-tracker)
