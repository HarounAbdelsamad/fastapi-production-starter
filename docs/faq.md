# FAQ

## General

**Is this a SaaS starter or a full-stack template?**

Neither. This is a backend-only API foundation.  There is no frontend, no billing logic,
and no email provider.  Pair it with your existing frontend stack (React, Next.js, etc.)
and plug in your preferred email and payment providers.  See
[ADR-010](adr/010-no-frontend.md) for the reasoning.

**Can I use this for a greenfield project?**

Yes.  Clone, rename, adjust the settings, and build on top.  The Cookiecutter template
(`cookiecutter.json`) lets you parameterise the project name and initial settings.

---

## Database

**Why are all three databases (Postgres, MySQL, SQLite) tested in CI?**

Enterprise environments use a variety of databases.  The CI matrix catches
database-specific SQL that would silently break for teams on a different engine.  SQLite
is used locally for speed; Postgres is the production default.  See
[ADR-003](adr/003-multi-db-support.md).

**Can I drop MySQL/SQLite and run Postgres only?**

Yes.  The CI matrix is just configuration.  The application code is database-agnostic
(SQLAlchemy abstracts the dialect).  Remove the MySQL/SQLite jobs from `.github/workflows/ci.yml`
if you only care about Postgres.

**Why async SQLAlchemy?**

FastAPI is async-native.  Synchronous SQLAlchemy blocks the event loop under load.
`AsyncSession` + `asyncpg`/`aiosqlite` keeps everything non-blocking.  See
[ADR-002](adr/002-why-sqlalchemy-2.md).

---

## Auth

**Can I add LDAP / Active Directory?**

LDAP is not built in.  The typical path is:

1. Add a SAML 2.0 IdP that federates with your AD (Azure AD, Okta, PingFederate).
2. Use the existing SAML flow.  Most enterprise AD deployments already have a SAML IdP.

**Does the SAML implementation support SP-initiated and IdP-initiated flows?**

SP-initiated only in the base implementation.  IdP-initiated can be added — it requires
accepting an unsolicited `SAMLResponse` at the ACS endpoint and skipping the `RelayState`
check.

**What's the token revocation strategy?**

When `TOKEN_REVOCATION_ENABLED=true`, revoked JTIs are stored in the `revoked_tokens`
table and checked on every authenticated request.  This adds one DB read per request;
use Redis if latency is a concern.  Set `TOKEN_REVOCATION_ENABLED=false` if you rely on
short-lived tokens and don't need explicit revocation.

---

## Observability

**I set `OTLP_ENDPOINT` but no spans appear in Jaeger. What's wrong?**

1. Check the endpoint includes the port: `http://jaeger:4317` (gRPC) not just `jaeger`.
2. Ensure `OTEL_SDK_DISABLED=false` (the default).
3. Verify the Jaeger container is reachable from your API container (same Docker network).
4. Check for TLS — if Jaeger requires TLS, use `OTLPSpanExporter(..., insecure=False)`.

**Does OpenTelemetry add overhead in production?**

Minimal when using `ParentBased(TraceIdRatioBased(...))` sampler.  Set
`OTEL_SAMPLE_RATE=0.1` to sample 10% of traces.  The SDK adds ~0.5 ms per sampled
request on typical hardware.  Set `OTEL_SDK_DISABLED=true` to remove all overhead.

---

## Compliance

**What does "HMAC-signed audit log" mean in practice?**

Each audit row has a `hmac_signature` column containing
`HMAC-SHA256(canonical_row_string, SECRET_KEY)`.  This proves the row hasn't been
tampered with after write.  Verify offline with `verify_audit_log(row, secret)`.
See [compliance/audit-log.md](compliance/audit-log.md).

**Does the GDPR pseudonymization actually delete PII?**

Yes.  `pseudonymize_user` replaces every field registered via `@mark_pii()` with a
deterministic hash (`deleted-{sha256[:16]}`).  The user row is soft-deleted
(`deleted_at` set).  Referential integrity (FK columns pointing at `user_id`) is
preserved.  Call `delete_user_data` after pseudonymisation for a hard-delete of the
user row.

---

## Operations

**The idempotency middleware uses an in-process dict by default — is that a problem?**

For single-instance deployments it's fine.  For multi-instance (horizontal scaling),
set `CACHE_ENABLED=true` to move the idempotency store to Redis, which is shared across
instances.

**How do I consume pending webhook retries?**

Retries are not automatically re-sent — the current implementation records
`next_retry_at` and waits for the replay endpoint or a periodic task.  To build
auto-retry, add a Celery beat task that queries `WebhookDelivery` rows where
`status="pending"` and `next_retry_at <= now()` and calls `replay_delivery`.

---

## Development

**Why uv instead of pip / Poetry?**

`uv` is significantly faster for dependency resolution and virtual-environment creation.
The `uv.lock` file provides reproducible installs.  See
[uv documentation](https://docs.astral.sh/uv/).

**The test suite requires ≥50% coverage but my new feature is not tested. Will CI fail?**

Yes.  Add at least a smoke test for your feature.  The coverage threshold is a
floor, not a target — the goal is to catch untested paths, not to game a number.

**Can I use this as a Cookiecutter template?**

Yes.  `cookiecutter.json` at the repo root defines the template parameters.  Run:

```bash
pip install cookiecutter
cookiecutter gh:HarounAbdelsamad/fastapi-production-starter
```
