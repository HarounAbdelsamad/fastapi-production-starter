# ADR-003: Multi-DB Support Boundaries

## Status
Accepted

## Context

One of the core differentiators of this template is multi-database support: PostgreSQL, MySQL, and SQLite tested and documented. This is not a claim that all features work identically on all databases. It is a claim that the template's core patterns work on all three, and that the differences are honestly documented.

This ADR defines:
- What "multi-DB support" means in this context
- Which features are tested on which databases
- Which features are Postgres-only (by design or limitation)
- The CI matrix setup

## Decision

**Test core functionality against PostgreSQL 16, MySQL 8, and SQLite (latest). Document per-database limitations explicitly. Do not claim feature parity — claim tested compatibility with documented caveats.**

## What We Test (CI Matrix)

All three databases are tested in the CI matrix on every PR and push to main:

| Test area | Postgres | MySQL | SQLite |
|---|---|---|---|
| Auth flows (login, refresh, logout) | ✓ | ✓ | ✓ |
| User CRUD | ✓ | ✓ | ✓ |
| Alembic migrations (up + down) | ✓ | ✓ | ✓ |
| Multi-tenancy (row-level isolation) | ✓ | ✓ | ✓ |
| Audit log writes + HMAC verification | ✓ | ✓ | ✓ |
| Feature flags | ✓ | ✓ | ✓ |
| Connection pool behavior | ✓ | ✓ | N/A |

## What We Do NOT Test (and Why)

| Feature | Status | Reason |
|---|---|---|
| JSON column operators (`->`, `->>`) | Postgres-only | MySQL has JSON support but different operators; SQLite has limited JSON support. Use `Text` columns + application-layer JSON parsing for cross-DB portability. |
| Full-text search | Not tested | Each DB has different FTS syntax and capabilities. Use a dedicated search layer (Meilisearch, Elasticsearch, Typesense) for production FTS. |
| `RETURNING` clause in INSERT/UPDATE | Postgres best | MySQL 8+ supports it partially; SQLite 3.35+. We avoid relying on it in cross-DB code paths. |
| Array columns | Postgres-only | Use JSON columns or a related table for cross-DB portability. |
| Window functions | Postgres/MySQL | SQLite has basic window function support since 3.25. We test only simple aggregations. |
| Generated columns | Postgres 12+ / MySQL 5.7+ | Not used in core code paths. |
| Row-level locking (`SELECT ... FOR UPDATE`) | Postgres/MySQL | SQLite uses file-level locking. Pessimistic locking patterns are documented as Postgres/MySQL only. |
| UUID primary keys | ✓ all (via `Uuid` type) | SQLAlchemy's `Uuid` type handles storage differences. |
| Enum columns | ✓ all (via `Enum` type) | Stored as VARCHAR on MySQL/SQLite; native ENUM on Postgres. |

## Database-Specific Configuration

### PostgreSQL (primary target)
```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
```
- Full feature support
- Recommended for production
- Connection pool: asyncpg (via SQLAlchemy's asyncpg dialect)

### MySQL 8+
```
DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/dbname
```
- Known limitation: no native array types (use JSON or separate table)
- Known limitation: case-insensitive collation default differs from Postgres (set `utf8mb4_bin` for case-sensitive where needed)
- Known limitation: no `RETURNING` clause support for bulk inserts
- Requires `aiomysql` or `asyncmy` driver

### SQLite
```
DATABASE_URL=sqlite+aiosqlite:///./dev.db
```
- For development and testing only
- No connection pooling (file locking)
- WAL mode recommended for concurrent reads: `PRAGMA journal_mode=WAL`
- Not recommended for production multi-user deployments

## Why MySQL and SQLite at All?

**MySQL:** Many enterprise environments run MySQL. A template that only supports Postgres limits adoption in shops that standardized on MySQL (common in companies with Java/Ruby legacy stacks). Supporting MySQL costs little with SQLAlchemy handling most of the differences.

**SQLite:** The development experience without requiring a running database service matters. Developers without Docker running locally, CI jobs that spin up quickly, embedded deployments. SQLite support also forces the codebase to stay free of Postgres-isms that would otherwise creep in silently.

## Alembic and Multi-DB

Migration scripts use SQLAlchemy's generic type system (`String`, `Integer`, `DateTime`, `Boolean`, `Text`, `Uuid`, `JSON`). Scripts avoid:
- Raw SQL DDL that uses DB-specific syntax
- Postgres-specific types (`ARRAY`, `JSONB`, `INET`, `CIDR`, `TSVECTOR`)
- MySQL-specific column options (`UNSIGNED`, `AUTO_INCREMENT` — use `autoincrement=True` on the column)

When Postgres-specific features are needed for performance (e.g., `JSONB` indexing, `GIN` indexes), they are wrapped in `op.execute()` with a dialect check so the migration degrades gracefully on other databases.

## Consequences

**Positive:**
- CI matrix catches Postgres-isms before they ship. Engineers can't accidentally use `RETURNING` and break MySQL deployments.
- Teams on MySQL or embedded deployments can adopt the template.
- Honest documentation of limitations builds more trust than overclaiming.

**Negative:**
- CI runtime increases proportionally with the matrix. Three databases × test suite time. Mitigated by running unit tests on SQLite only, integration tests on all three.
- Some Postgres features are off the table for core code paths. Teams that need `JSONB` indexing or `ARRAY` types can add them in their fork; the template won't use them in shared code.
- MySQL's collation defaults are different from Postgres. Text comparison behavior can differ. Documented explicitly.

## References

- [SQLAlchemy dialect documentation](https://docs.sqlalchemy.org/en/20/dialects/)
- [Alembic autogenerate limitations](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
