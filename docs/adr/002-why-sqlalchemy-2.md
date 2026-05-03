# ADR-002: Why SQLAlchemy 2.0 over Alternatives

## Status
Accepted

## Context

The data access layer is the second most sticky decision after the framework. It must support:

1. Multiple database backends (Postgres, MySQL, SQLite) — a core template feature
2. Async operation — required for FastAPI's async handlers
3. A rich migration story via Alembic
4. Type safety that integrates with Pydantic

Candidate options:

- **SQLAlchemy 2.0** with async support
- **Tortoise ORM** — async-native Django-style ORM
- **Peewee** — lightweight ORM
- **SQLModel** — thin layer over SQLAlchemy + Pydantic
- **raw SQL** via databases or asyncpg

## Decision

**Use SQLAlchemy 2.0 with async sessions (`AsyncSession`), paired with Alembic for migrations.**

SQLModel is explicitly considered and rejected as the primary interface (though it can be used alongside).

## Reasoning

### SQLAlchemy 2.0 Core + ORM

SQLAlchemy is the de facto standard ORM in the Python ecosystem. The 2.0 release brought:

- **Native async support** via `AsyncSession` and `create_async_engine` — no greenlet tricks required
- **Cleaner type annotations** — mapped classes are typed, `select()` statements return typed results
- **Unified Core and ORM syntax** — `select(User).where(User.id == id)` works in both contexts
- **Multi-DB abstraction** — the dialect system handles Postgres, MySQL, SQLite, Oracle, MSSQL differences transparently

SQLAlchemy's dialect system is the primary reason it is chosen here over every alternative. No other Python ORM has the same breadth of tested, production-grade database support.

### Tortoise ORM

Tortoise ORM is async-native and uses a Django-style declarative API. It is a legitimate choice for async-first projects, but has several issues for this use case:

- **Limited dialect support**: Postgres and MySQL are solid; SQLite support has quirks; other enterprise DBs have minimal or no support
- **Alembic incompatibility**: Tortoise has its own migration tool (`aerich`), which is less mature than Alembic and lacks Alembic's branching and merging capabilities
- **Smaller ecosystem**: Far fewer third-party libraries, fewer production deployments at scale
- **Type inference**: Tortoise's type story is weaker than SQLAlchemy 2.0's

### Peewee

Peewee is synchronous. Async wrappers (peewee-async) exist but are not officially maintained at the same level. For a FastAPI foundation, synchronous ORM access inside async handlers is an anti-pattern that blocks the event loop. Ruled out.

### SQLModel

SQLModel, created by the FastAPI author, combines SQLAlchemy models with Pydantic models. It reduces boilerplate for simple CRUD. Reasons it is not the primary interface:

- **Abstraction leaks**: SQLModel hides SQLAlchemy complexity until it doesn't — complex queries, relationships, and migrations require falling back to raw SQLAlchemy anyway. The template would teach two APIs.
- **Version coupling**: SQLModel's SQLAlchemy 2.0 support has lagged behind. Teams using the template would be blocked by SQLModel's release cadence.
- **Enterprise patterns**: Bulk inserts, complex joins, subqueries, window functions — all require SQLAlchemy Core directly.

SQLModel can be used alongside this template for simple models. We default to SQLAlchemy 2.0 directly.

### Raw SQL via `databases` or `asyncpg`

Raw SQL gives maximum control and performance, at the cost of:

- No migration support (Alembic can not introspect raw SQL models)
- No type safety on query results
- No multi-DB abstraction (Postgres-specific syntax throughout)
- Significant boilerplate for every entity

Acceptable for high-performance query paths or legacy schemas. Not appropriate for a general-purpose enterprise foundation.

## Consequences

**Positive:**
- The dialect system means the same model code runs on Postgres, MySQL, and SQLite without changes (within documented limitations — see ADR-003).
- Alembic provides enterprise-grade migration management: branching, merging, downgrade support, autogenerate.
- SQLAlchemy 2.0's typed API catches bugs at development time via mypy/pyright.
- `AsyncSession` works correctly in FastAPI's `async def` handlers without blocking the event loop.
- Massive ecosystem: SQLAlchemy is understood by every senior Python engineer.

**Negative:**
- SQLAlchemy has a steeper learning curve than Peewee or Tortoise. The 2.0 API is cleaner than 1.x but still requires understanding the session/identity map model.
- Async SQLAlchemy requires careful session management (one session per request, not shared). The template provides the correct pattern via `Depends()`.
- `AsyncSession` has subtleties around lazy loading (it is disabled by default — all relationships must be explicitly loaded). This is correct behavior but surprises developers coming from synchronous SQLAlchemy.

## References

- [SQLAlchemy 2.0 migration guide](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html)
- [SQLAlchemy async documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/)
