# Migrating from tiangolo/full-stack-fastapi-template

This guide is for teams currently using [tiangolo/full-stack-fastapi-template](https://github.com/tiangolo/full-stack-fastapi-template) who are evaluating or moving to `fastapi-production-starter`.

## Should You Migrate?

First, be honest about whether migration is the right choice for your project.

**Migrate if:**
- You are dropping the React frontend (or have already replaced it)
- You need SAML 2.0, multi-DB support, or OpenTelemetry as first-class features
- You are serving enterprise clients with compliance requirements (audit logs, GDPR helpers)
- Your team is backend-focused and the bundled frontend creates friction

**Stay with tiangolo's template if:**
- You actively use the React frontend and are happy with it
- You are building a straightforward CRUD SaaS with Postgres only
- You don't need enterprise identity (SAML, API keys, multi-IdP)
- You value the template's wider community adoption and more examples

There is no shame in using the right tool. If tiangolo's template fits your project, use it.

## What's Different

| Dimension | tiangolo/full-stack-fastapi | fastapi-production-starter |
|---|---|---|
| Frontend | React + Vite (bundled) | None — backend only |
| Database | PostgreSQL only | Postgres + MySQL + SQLite (CI-tested) |
| Auth | JWT + basic OAuth | JWT + OAuth + SAML (roadmap) + API keys (roadmap) |
| Observability | Basic logging | OpenTelemetry (default, noop exporter) |
| Audit log | None | HMAC-signed append-only log |
| Secrets | `.env` only | Protocol + Vault/AWS adapters |
| Multi-tenancy | None | Row-level isolation built in |
| ADRs / docs | None | 12 ADRs + architecture docs |
| Admin UI | SQLModel Admin | None (API endpoints only) |
| Email | Built-in | Protocol only (bring your provider) |

## Migration Path

This is not a mechanical migration — the two templates have different structural assumptions. Treat this as a **porting** exercise, not a diff-and-apply.

### Step 1: Inventory What You Are Using

Before touching any code, list what you actively use from tiangolo's template:

- [ ] React frontend — are you keeping it? (If yes, reconsider migration)
- [ ] SQLModel models — how many entities do you have?
- [ ] Auth (JWT login, password reset)
- [ ] Email (password reset emails, notifications)
- [ ] Admin UI (SQLModel Admin)
- [ ] Background tasks (any Celery/async tasks wired in)
- [ ] Postgres-specific features (JSONB columns, pg-specific SQL in migrations)

### Step 2: Port Your Data Models

tiangolo's template uses **SQLModel** (a combined SQLAlchemy + Pydantic layer). This template uses **SQLAlchemy 2.0** models separately from **Pydantic** schemas.

**tiangolo pattern:**
```python
# SQLModel — combines DB model and API schema in one class
class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
```

**This template's pattern:**
```python
# SQLAlchemy ORM model
class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))

# Separate Pydantic schema for API
class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    model_config = ConfigDict(from_attributes=True)
```

The separation is more verbose but provides cleaner separation of concerns: the DB model does not leak into API responses, and you can evolve them independently.

For each SQLModel in tiangolo's template, create:
1. A SQLAlchemy mapped class in `app/models/`
2. A Pydantic schema in `app/schemas/`

### Step 3: Port Your Migrations

tiangolo uses Alembic too, so migration files can often be ported. Key differences:

1. Check for `sa.Column(postgresql.UUID(...))` — replace with `sa.Column(sa.Uuid())` for multi-DB compatibility
2. Check for `sa.Column(postgresql.JSONB())` — if you need this, keep it but document it as Postgres-only (see [ADR-003](adr/003-multi-db-support.md))
3. Check for `server_default=sa.text("gen_random_uuid()")` — replace with `sa.text("(lower(hex(randomblob(4))) || '-' || ...)")` or use application-level UUID generation (recommended)

The safest approach: export your current data, start fresh with this template's migrations, re-import.

### Step 4: Port Auth Logic

Both templates use JWT. The token structure may differ:

**tiangolo claims:**
```json
{"sub": "user-uuid", "exp": 1234567890}
```

**This template's claims:**
```json
{"sub": "user-uuid", "tenant_id": "tenant-uuid", "roles": ["user"], "exp": 1234567890}
```

If you are adding multi-tenancy or RBAC, the migration is a good time to add these claims. If not, you can remove `tenant_id` from the token claims.

Password hashing: both templates use bcrypt. Existing hashed passwords are compatible.

### Step 5: Port API Routes

Route structure is similar:
- tiangolo: `/api/v1/users/`, `/api/v1/login/access-token`
- This template: `/api/v1/users/`, `/api/v1/auth/login`

Map your existing routes to this template's router structure in `app/routers/`. The versioned prefix (`/api/v1/`) is the same.

### Step 6: Remove or Replace the Frontend

If you are dropping the React frontend:
1. Remove the `frontend/` directory
2. Remove frontend-related Docker Compose services
3. Update CORS settings in `app/core/config.py` — `CORS_ORIGINS` now points to wherever your frontend will live

If you are keeping the React frontend (paired separately):
1. Point it at the new backend's API base URL
2. Update the auth flow to match this template's token endpoint (`POST /api/v1/auth/login` returns `{access_token, refresh_token}`)
3. Add the `X-Request-ID` header handling if you want correlation IDs in frontend error reports

### Step 7: Remove the SQLModel Admin UI

tiangolo ships SQLModel Admin at `/admin`. This template does not include it. Options:

1. **Add it back**: Install `sqladmin` and register it — it works with SQLAlchemy 2.0 directly.
2. **Use the API endpoints**: `/api/v1/admin/dashboard` and `/api/v1/admin/audit-logs` provide admin data via API.
3. **Build a minimal admin**: A small FastAPI HTML router with Jinja2 templates for internal tools use cases.

### Step 8: Replace Email with a Protocol

tiangolo has a built-in email service with templates. This template does not include an email implementation — only the interface points for where email would be sent (password reset, user invitations).

Wire in your email provider of choice:
- **Resend**: straightforward HTTP API, easiest to integrate
- **AWS SES**: standard for AWS-deployed services
- **SendGrid**: common enterprise choice

The password reset flow calls `email_service.send_password_reset(email, token)`. Implement that interface with your provider.

### Common Pitfalls

**JSONB columns**: If your tiangolo project uses `JSONB` extensively (Postgres-specific), you have a choice: keep them (Postgres-only, document it) or migrate to `JSON` type (portable, slower for complex queries). For most use cases, `JSON` is sufficient.

**SQLModel relationships**: SQLModel's relationship syntax differs from SQLAlchemy 2.0's `relationship()`. Port each relationship to the explicit SQLAlchemy 2.0 syntax.

**Alembic autogenerate**: After porting models, run `alembic revision --autogenerate -m "initial"` against a fresh database to generate a clean baseline migration. Do not try to patch tiangolo's migration history.

**UUID primary keys**: Both templates use UUIDs as primary keys. The storage format differs by DB (native UUID on Postgres, CHAR(32) on MySQL, TEXT on SQLite). SQLAlchemy's `Uuid` type handles this correctly.

## What You Get After Migration

- Multi-DB support if you need to add MySQL later
- OpenTelemetry traces wired in (add `OTLP_ENDPOINT` to see them)
- HMAC-signed audit log for every material action
- SAML 2.0 support when you need enterprise SSO
- Pluggable secrets backend for Vault or AWS Secrets Manager
- Row-level multi-tenancy built into the foundation
- 12 ADRs documenting why each decision was made

## Getting Help

Open a [GitHub Discussion](https://github.com/HarounAbdelsamad/fastapi-production-starter/discussions) with your migration question. Include:
- What version of tiangolo's template you are migrating from
- Which specific part of the migration is causing issues
- The error message or unexpected behavior you are seeing
