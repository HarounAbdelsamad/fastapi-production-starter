# Architecture Overview

> **Placeholder** — this diagram will be replaced with a detailed architecture diagram in Phase 1.

```mermaid
graph TB
    Client["Client (Browser / Service)"]

    subgraph Gateway["API Gateway Layer"]
        RateLimit["Rate Limiting"]
        AuthMiddleware["Auth Middleware (JWT / API Key / SAML)"]
        RequestID["Request ID + Security Headers"]
    end

    subgraph App["FastAPI Application"]
        Routers["Routers (v1)"]
        Services["Services"]
        Core["Core (config, security, logging, OTel)"]
    end

    subgraph Identity["Identity & Access"]
        JWT["JWT / Refresh"]
        OAuth["OAuth (Google, GitHub)"]
        SAML["SAML 2.0 (Keycloak)"]
        APIKey["API Keys"]
        RBAC["RBAC + Permissions"]
    end

    subgraph Data["Data Layer"]
        SQLAlchemy["SQLAlchemy 2.0"]
        Postgres[("PostgreSQL")]
        MySQL[("MySQL")]
        SQLite[("SQLite")]
        Alembic["Alembic Migrations"]
    end

    subgraph Observability["Observability"]
        OTel["OpenTelemetry SDK"]
        Prometheus["Prometheus Metrics"]
        StructuredLogs["Structured JSON Logs"]
    end

    subgraph Background["Background / Async"]
        Celery["Celery Worker"]
        Redis[("Redis")]
    end

    subgraph Compliance["Compliance"]
        AuditLog["Audit Log (HMAC signed)"]
        GDPR["GDPR Export / Pseudonymize"]
    end

    Client --> Gateway
    Gateway --> App
    App --> Identity
    App --> Data
    App --> Observability
    App --> Background
    App --> Compliance
    Data --> Postgres
    Data --> MySQL
    Data --> SQLite
    Background --> Redis
```

## Layer Descriptions

| Layer | Responsibility |
|---|---|
| API Gateway | Rate limiting, auth dispatch, request enrichment |
| FastAPI Application | Routing, business logic, dependency injection |
| Identity & Access | Multi-IdP auth, RBAC, API key lifecycle |
| Data Layer | Multi-DB abstraction, zero-downtime migrations |
| Observability | Traces, metrics, structured logs — OTel by default |
| Background | Async task queue (Celery default, RQ adapter sketch) |
| Compliance | Audit log, GDPR helpers, PII field tagging |

All features are **toggleable via environment variables** and off by default in development.
