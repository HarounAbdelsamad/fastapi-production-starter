# ADR-001: Why FastAPI over Flask, Django, and Litestar

## Status
Accepted

## Context

Choosing the right Python web framework is the foundational architectural decision for this template. The framework shapes the developer experience, the testing story, the deployment model, and how enterprise patterns (auth middleware, DI, OpenAPI) are implemented. This decision is sticky — changing frameworks later would require a full rewrite.

The candidate frameworks are:

- **Flask** — the incumbent micro-framework
- **Django** — the batteries-included framework
- **FastAPI** — the modern async-first framework
- **Litestar** (formerly Starlette-based) — the newcomer

Enterprise requirements that inform this decision:

1. First-class async support (I/O-heavy backends, long-running connections)
2. Automatic OpenAPI / JSON Schema documentation (enterprise teams require it for API governance)
3. Strong type checking support (reduces bugs, improves tooling)
4. Native dependency injection (for pluggable auth, secrets, observability)
5. Production adoption at scale (risk of choosing an abandoned framework)

## Decision

**Use FastAPI.**

## Reasoning

### Flask
Flask is a solid framework but was designed for a synchronous world. Adding async to Flask requires Quart or careful `asyncio.run()` wrappers that break in non-obvious ways under load. It has no built-in DI, no type validation, and no auto-generated API docs. Enterprise teams using Flask typically build all of these on top — which is exactly what this template would be doing for them. The value-add over plain Flask narrows. Flask has a large ecosystem but the FastAPI ecosystem for API-first backends is now larger on most dimensions that matter here.

### Django
Django is excellent for its intended use case: content-driven web apps where the ORM, admin, and form handling all work together. For an API-first backend foundation, Django carries significant weight: its ORM is not SQLAlchemy (making multi-DB or migration portability harder), its async story is still maturing, and its conventions are optimized for the full-stack use case. Using Django for a backend-only API foundation means fighting the framework's conventions. Django REST Framework (DRF) is mature but adds another layer. The Django admin is not needed. The Django ORM is not needed. What remains is request routing and middleware — at that point, a lighter framework is more appropriate.

### Litestar
Litestar (formerly APIFire, then Starlite) is the most technically comparable alternative. It is async-first, type-annotated, has DI, and generates OpenAPI. The substantive reasons to prefer FastAPI at this time:

- **Ecosystem size**: FastAPI has a significantly larger community, more integrations, and more production deployments. For a template aimed at enterprise adoption, ecosystem maturity reduces risk.
- **Stability track record**: FastAPI has been stable longer. Litestar had a rename and API shifts through its early versions.
- **SQLAlchemy integration**: FastAPI's integration with SQLAlchemy (via SQLModel or direct) is more thoroughly documented and battle-tested.
- **Hiring/familiarity**: Enterprise teams evaluating this template will have more FastAPI engineers on staff.

Litestar is a legitimate alternative and will likely narrow the gap over time. The decision would be revisited if Litestar's ecosystem reaches parity.

### FastAPI
FastAPI's advantages for this use case:

- **Pydantic v2 integration**: Request/response validation with no boilerplate. Pydantic v2 is materially faster than v1 and enterprise-grade.
- **Automatic OpenAPI**: Every endpoint documented with request/response schemas. Enterprise API governance teams require this.
- **Async-first**: `async def` handlers, async DB sessions, no thread pool hacks.
- **Starlette underneath**: Battle-tested ASGI foundation. Middleware, lifespan, websockets all from a stable base.
- **Dependency injection**: Native DI via `Depends()` makes pluggable auth, per-request sessions, and feature toggles straightforward to implement and test.
- **Production adoption**: Used by Microsoft, Netflix, Uber (Orion), and many others at enterprise scale.

## Alternatives Ruled Out

- **Tornado, Sanic, aiohttp**: Lower-level, require more boilerplate for enterprise patterns. Not the right abstraction level for a starter template.
- **gRPC (via grpcio)**: Out of scope for v0.1. REST/OpenAPI is the standard for the target audience. gRPC support is on the v0.2 roadmap.

## Consequences

**Positive:**
- Auto-generated OpenAPI spec is always current — no separate documentation maintenance.
- Pydantic validates at the boundary; internal code can trust that models are valid.
- `Depends()` DI makes every major concern (auth, DB session, tenant context) injectable and testable.
- Async-first means connection pooling and background tasks work correctly under load.

**Negative:**
- FastAPI's DI system has a learning curve for engineers new to it. Documented in the quickstart.
- Pydantic v2 has breaking changes from v1; projects migrating from older FastAPI versions may need model updates. This template targets v2 only.
- No built-in admin UI. Enterprise teams need to build their own or integrate a third-party option. Documented explicitly as out-of-scope.

## References

- [FastAPI documentation](https://fastapi.tiangolo.com)
- [Starlette documentation](https://www.starlette.io)
- [Pydantic v2 migration guide](https://docs.pydantic.dev/latest/migration/)
