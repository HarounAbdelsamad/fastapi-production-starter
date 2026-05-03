# Architecture Decision Records

This file indexes the Architecture Decision Records (ADRs) for `fastapi-production-starter`. Each ADR documents a significant design choice: the context that forced a decision, the decision itself, the alternatives considered, and the consequences.

ADRs are numbered sequentially. New ADRs are added; existing ADRs are not modified (decisions are not revisited in place — a new ADR supersedes an old one if the decision changes).

## Index

| ADR | Title | Status | Summary |
|---|---|---|---|
| [ADR-001](../adr/001-why-fastapi.md) | Why FastAPI over Flask, Django, Litestar | Accepted | FastAPI's async-first design, Pydantic v2 integration, auto-OpenAPI, and native DI make it the right foundation for an enterprise API. Flask lacks async; Django is optimized for full-stack; Litestar has a smaller ecosystem. |
| [ADR-002](../adr/002-why-sqlalchemy-2.md) | Why SQLAlchemy 2.0 | Accepted | SQLAlchemy 2.0's dialect system is the only Python ORM with production-grade support for Postgres, MySQL, and SQLite. Async sessions via `AsyncSession` work correctly with FastAPI. Alembic migration support is unmatched. |
| [ADR-003](../adr/003-multi-db-support.md) | Multi-DB support boundaries | Accepted | Postgres, MySQL, SQLite are tested in CI. Postgres-specific features (JSONB, ARRAY, FTS) are explicitly excluded from cross-DB code paths. Limitations are documented honestly. |
| [ADR-004](../adr/004-pluggable-secrets.md) | Pluggable secret backend protocol | Accepted | A `SecretsProvider` protocol with an `EnvSecretsProvider` default. Vault and AWS Secrets Manager skeleton implementations shipped. Enterprise teams can implement their own backend in ~50 lines without forking. |
| [ADR-005](../adr/005-multi-tenancy.md) | Multi-tenancy strategy | Accepted | Shared database, row-level isolation via `tenant_id`. Simpler ops, single migration path, cross-tenant queries. Schema-per-tenant and DB-per-tenant documented as advanced patterns for high-compliance workloads. |
| [ADR-006](../adr/006-saml-library.md) | SAML library choice (python3-saml) | Accepted | `python3-saml` (OneLogin's library) is chosen for its production track record, active maintenance, and enterprise battle-testing. pysaml2 is more complex with an IdP-focused design. |
| [ADR-007](../adr/007-opentelemetry-default.md) | OpenTelemetry wired in by default | Accepted | OTel SDK initialized at startup with a noop exporter. Near-zero overhead when not exporting. Activating telemetry requires one env var (`OTLP_ENDPOINT`), not a code change. Opt-in observability means no observability. |
| [ADR-008](../adr/008-audit-log.md) | Audit log signing and storage | Accepted | HMAC-SHA256 per row using a configurable signing key. Same DB as application data (transactional writes). Append-only enforcement at application layer. Key rotation documented. |
| [ADR-009](../adr/009-background-jobs-protocol.md) | Background jobs as a protocol | Accepted | `JobQueue` protocol with a Celery adapter (default) and RQ reference adapter. Decouples application code from queue implementation. Teams can swap to Dramatiq, Arq, or cloud queues without touching business logic. |
| [ADR-010](../adr/010-no-frontend.md) | Why no frontend | Accepted | Backend-only. Enterprise teams have their own frontend stacks. A bundled frontend adds churn and scope without value for the target audience. The OpenAPI spec is the contract. |
| [ADR-011](../adr/011-toggleable-features.md) | Toggleable features pattern | Accepted | Two tiers: env-time toggles for infrastructure (require restart), runtime feature flags for business logic (DB-backed, no restart). Explicit separation prevents misuse of either mechanism. |
| [ADR-012](../adr/012-versioning-compatibility.md) | Versioning and API compatibility | Accepted | Semantic versioning for the template. URL path versioning (`/api/v1/`) for the API. 12-month deprecation window for breaking changes in `1.x` releases. |

## How to Write a New ADR

When making a significant architectural decision, create a new ADR:

```bash
# Create the file
touch docs/adr/013-your-decision-title.md

# Use this template:
```

```markdown
# ADR-013: Title

## Status
Proposed | Accepted | Deprecated | Superseded by ADR-NNN

## Context
What is the situation that forces a decision? What constraints exist?

## Decision
What is the decision?

## Alternatives Considered
What else was evaluated? Why was each rejected?

## Consequences
What becomes easier? What becomes harder? What are the known trade-offs?

## References
Links to relevant external resources, prior art, specs.
```

Then add a row to the index table in this file.

## What Belongs in an ADR

ADRs are for decisions that:
- Are hard to reverse
- Have significant trade-offs
- Would confuse a future contributor if they found the code without context
- Involve a choice between multiple legitimate alternatives

ADRs are **not** for:
- Documenting how a feature works (that belongs in the feature's doc page)
- Recording implementation details (those belong in code comments)
- Capturing requirements (those belong in issues or project docs)
