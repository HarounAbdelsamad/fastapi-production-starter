# Multi-Database Support Matrix

`fastapi-production-starter` is tested against **PostgreSQL 16**, **MySQL 8**, and **SQLite** on every CI run. This page documents what is supported, what is limited, and what is explicitly unsupported on each database.

For the rationale behind multi-DB support and the CI strategy, see [ADR-003](../adr/003-multi-db-support.md).

---

## Quick Reference

| Feature | PostgreSQL 16 | MySQL 8 | SQLite |
|---|---|---|---|
| **Async driver** | asyncpg | aiomysql | aiosqlite |
| **Core CRUD** | ✓ | ✓ | ✓ |
| **Alembic migrations** | ✓ | ✓ | ✓ (batch mode) |
| **UUID primary keys** | ✓ (native) | ✓ (CHAR 36) | ✓ (TEXT) |
| **JSON columns** | ✓ (`JSON`) | ✓ (`JSON`) | ✓ (TEXT) |
| **JSONB / JSON operators** | ✓ (Postgres only) | ✗ | ✗ |
| **Full-text search** | ✓ (via `tsvector`) | ✓ (FULLTEXT) | limited |
| **`RETURNING` clause** | ✓ | limited (8.0.21+) | limited (3.35+) |
| **Array columns** | ✓ (Postgres only) | ✗ | ✗ |
| **Row-level locking** | ✓ | ✓ | ✗ (file-level) |
| **Window functions** | ✓ | ✓ | ✓ (3.25+) |
| **Generated columns** | ✓ (12+) | ✓ (5.7+) | ✓ (3.31+) |
| **Connection pooling** | ✓ (asyncpg) | ✓ (aiomysql) | N/A |
| **Recommended for production** | ✓ | ✓ | Dev / embedded only |

---

## Feature Details

### UUID Primary Keys

SQLAlchemy's `Uuid` type maps to the appropriate storage type per database:

| DB | Storage |
|---|---|
| PostgreSQL | `UUID` (native 16-byte) |
| MySQL | `CHAR(36)` |
| SQLite | `TEXT` |

All three work correctly with the `Uuid` mapped column type. No application code changes required.

### JSON Columns

Use `sa.JSON` in migrations (not `sa.JSONB`). SQLAlchemy maps:

| DB | Storage |
|---|---|
| PostgreSQL | `JSON` |
| MySQL | `JSON` (validated by engine) |
| SQLite | `TEXT` (application-level JSON) |

**If you need JSON operators** (`->`, `->>`, `@>`, `?`), you are using a Postgres-only feature. Document it in your code and in your ADRs. Do not use JSON operators in cross-DB code paths.

### Full-Text Search

Each database has different FTS syntax and capabilities. This template does not abstract FTS — it is out of scope for cross-DB code paths. Recommendations:

- **PostgreSQL**: use `tsvector` columns + `GIN` indexes. Powerful but Postgres-only.
- **MySQL**: use `FULLTEXT` indexes on `TEXT`/`VARCHAR` columns.
- **Production FTS**: use a dedicated search service (Meilisearch, Typesense, Elasticsearch) for real-world full-text search. This decouples search from your primary DB.

### Alembic Migrations

All migration scripts use generic SQLAlchemy types. SQLite requires batch mode for `ALTER TABLE` operations (adding/removing/renaming columns). Alembic batch mode is enabled automatically when `DATABASE_URL` starts with `sqlite`:

```python
# alembic/env.py
render_as_batch = settings.is_sqlite
```

Batch mode wraps each `ALTER TABLE` in a full table copy-and-rename, which is slower but correct.

### Row-Level Locking (`SELECT FOR UPDATE`)

PostgreSQL and MySQL support `SELECT ... FOR UPDATE` for pessimistic locking. SQLite uses file-level locking — row-level pessimistic locking is not available.

Cross-DB code that requires row-level locking should:
1. Use optimistic locking (version column) as the cross-DB approach
2. Fall back to `SELECT FOR UPDATE` as a Postgres/MySQL-only optimisation

### `RETURNING` Clause

Used to get the inserted/updated row back without a second SELECT. Support varies:

| DB | Support |
|---|---|
| PostgreSQL | Full support |
| MySQL 8.0.21+ | `RETURNING` in INSERT only |
| SQLite 3.35+ | `RETURNING` support |

Avoid `RETURNING` in Alembic migrations and cross-DB service code. Use a follow-up `SELECT` instead, which works on all three.

---

## Connection String Reference

### PostgreSQL (production recommended)

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
```

Driver: `asyncpg` (included in default dependencies)

Tuning parameters: see [Connection Pooling](connection-pooling.md).

### MySQL 8

```bash
DATABASE_URL=mysql+aiomysql://user:pass@host:3306/dbname
```

Driver: `aiomysql` (included in default dependencies)

**Required charset setting**: MySQL defaults to `utf8mb4_0900_ai_ci` which is case-insensitive. If case-sensitive text comparisons matter (usernames, API keys):

```bash
DATABASE_URL=mysql+aiomysql://user:pass@host:3306/dbname?charset=utf8mb4
```

And create the database with:

```sql
CREATE DATABASE dbname CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
```

### SQLite

```bash
DATABASE_URL=sqlite+aiosqlite:///./dev.db
# or in-memory (tests):
DATABASE_URL=sqlite+aiosqlite:///:memory:
```

Driver: `aiosqlite` (included in default dependencies)

**WAL mode** (recommended for concurrent reads in development):

```python
# In alembic/env.py or app startup:
from sqlalchemy import event

@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()
```

---

## Adding a New Database

To add support for a new database (Oracle, MSSQL, CockroachDB, etc.):

1. Add the async driver to `pyproject.toml` dependencies
2. Verify `DATABASE_URL` uses the correct driver prefix (`oracle+oracledb://`, `mssql+aioodbc://`, etc.)
3. Audit migrations for any type incompatibilities using `alembic revision --autogenerate`
4. Add the database to the CI matrix in `.github/workflows/ci.yml`
5. Document limitations in this file

---

## Known Limitations

- **MySQL JSON**: JSON column indexing requires generated columns or a dedicated JSON index. Not supported in cross-DB migration scripts.
- **MySQL AUTO_INCREMENT**: Use `autoincrement=True` on the SQLAlchemy column, not raw `AUTO_INCREMENT` SQL.
- **SQLite ALTER TABLE**: Adding non-nullable columns with no default requires batch mode and careful migration design (use expand-contract; see [zero-downtime migrations](../migrations/zero-downtime.md)).
- **SQLite concurrency**: Not suitable for multi-process production deployments. Use Postgres or MySQL.
