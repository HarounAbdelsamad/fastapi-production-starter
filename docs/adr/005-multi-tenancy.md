# ADR-005: Multi-Tenancy Strategy

## Status
Accepted

## Context

Multi-tenancy is the ability for a single application deployment to serve multiple isolated customers ("tenants") from the same codebase and infrastructure. It is a requirement for most enterprise internal platforms and many B2B SaaS products.

The three standard approaches are:

1. **Shared database, row-level isolation**: All tenants share the same tables. Each row has a `tenant_id` column. Application code filters every query by `tenant_id`.
2. **Schema-per-tenant**: Each tenant gets a separate schema (namespace) within the same database. Tables are identical across schemas; access is controlled by switching the search path.
3. **Database-per-tenant**: Each tenant gets a completely separate database. The application manages a connection pool per tenant.

This template must choose a default strategy and document why, while acknowledging that enterprise teams will have different requirements.

## Decision

**Implement shared database, row-level isolation as the default. Document schema-per-tenant and database-per-tenant as advanced patterns in the docs, explaining when to consider each.**

## Reasoning

### Shared Database, Row-Level Isolation

**Chosen for the following reasons:**

**Operational simplicity**: One database, one connection pool, one migration run. No per-tenant provisioning step. Adding a tenant is an INSERT into the `tenants` table, not a database/schema CREATE operation.

**Single migration path**: Alembic migrations run once and affect all tenants simultaneously. Schema-per-tenant requires running migrations across N schemas (N can be hundreds), which is operationally complex and slow.

**Cross-tenant queries**: Internal analytics, billing aggregations, support queries — all require data from multiple tenants. Row-level isolation makes these queries straightforward. Schema-per-tenant requires a `UNION ALL` across schemas or a separate analytics layer.

**Cost**: One database instance serves all tenants. At small-to-medium scale, this is significantly cheaper than database-per-tenant.

**Tooling**: Every database tool (monitoring, backup, query analyzers) works against one target. Schema-per-tenant multiplies every operation by tenant count.

### Why Not Schema-Per-Tenant

Schema-per-tenant provides strong database-level isolation: a bug in tenant-filtering code cannot leak data between tenants because they are in different schemas. This is a real advantage for high-compliance workloads.

The costs:

- **Migration burden**: N migrations per schema per change. At 100 tenants, a 1-minute migration becomes 100 minutes or requires complex parallel orchestration.
- **Connection pool explosion**: Each schema needs a connection with the correct `search_path`. In practice this limits tenant count severely (hundreds, not thousands).
- **Cross-tenant access is complex**: Requires `UNION ALL` or a separate aggregation database.
- **Not portable**: Schema-based isolation is Postgres-specific. This template supports MySQL and SQLite, where schema isolation is not equivalent.

Schema-per-tenant is the right choice for high-security environments (healthcare, finance) where database-level isolation is a compliance requirement, and the tenant count is bounded (< 200). Documented as an advanced pattern.

### Why Not Database-Per-Tenant

Database-per-tenant provides the strongest isolation. Each tenant is completely separated at the infrastructure level. This is the right model for:

- Tenants in different geographic regions (data residency requirements)
- Tenants with different performance SLAs (dedicated connection pools)
- White-label products where tenants run self-hosted

The costs for a general-purpose template:

- **Connection pool management**: Each tenant requires active DB connections. At 1,000 tenants, this means 1,000+ DB connections at any time. Standard connection pool sizes (10–50 connections) times 1,000 tenants = 10,000–50,000 DB connections. Not feasible without a proxy layer (PgBouncer at scale).
- **Provisioning complexity**: Each new tenant requires infrastructure provisioning (creating a DB, running migrations, updating the connection registry). This is an operational workflow, not just an INSERT.
- **Monitoring and backup multiplication**: Every tool, every backup, every alert — multiplied by tenant count.

Database-per-tenant is documented as an advanced pattern for teams with data residency requirements.

## Implementation

### Tenant Identification

Tenants are identified by a `tenant_id` (UUID) attached to the request context early in the middleware stack. Identification strategies:

1. **Subdomain**: `tenant-a.app.example.com` → extract `tenant-a`, resolve to `tenant_id`
2. **HTTP header**: `X-Tenant-ID: <uuid>` (for API clients, internal services)
3. **JWT claim**: `tenant_id` embedded in the JWT payload (recommended for external clients)

The template uses JWT claim extraction by default. The middleware is pluggable.

### Tenant Context Propagation

A `TenantContext` object is injected via FastAPI's `Depends()`:

```python
async def get_tenant(token: TokenData = Depends(get_current_user)) -> Tenant:
    return await tenant_service.get_by_id(token.tenant_id)
```

Services receive the tenant context as a dependency. No global state. No thread-local.

### Query Filtering

All tenant-scoped repositories accept `tenant_id` as a parameter. SQLAlchemy's query construction makes this explicit:

```python
stmt = select(User).where(User.tenant_id == tenant_id)
```

There is no magic automatic filtering (unlike Django's row-level security). This is intentional: explicit is safer than magic. Missing a filter clause results in a test failure, not a silent data leak.

### Super-Admin Access

Admin users with the `SUPER_ADMIN` role bypass tenant filtering. This is explicitly gated and logged to the audit trail.

## Consequences

**Positive:**
- Simple operations. One DB, one migration, standard tooling.
- Cross-tenant queries are straightforward.
- Adding a tenant is an INSERT.
- Works on Postgres, MySQL, and SQLite without modification.

**Negative:**
- Tenant isolation is at the application layer, not the database layer. A bug in filtering logic can leak data across tenants. Mitigated by: explicit query parameters (no magic filtering), test suite that verifies tenant isolation for every resource type, code review checklist item.
- Shared database means one tenant's heavy queries can affect others. Mitigated by: connection pool limits per tenant (documented), query timeout configuration, read replica routing (ADR TBD).
- Not suitable for strict compliance environments that require database-level isolation (HIPAA, PCI DSS). These environments should use schema-per-tenant or database-per-tenant patterns. Documented.

## References

- [PostgreSQL row-level security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) — a more advanced alternative to application-layer filtering
- [Citusdata multi-tenancy guide](https://www.citusdata.com/blog/2016/10/03/designing-your-saas-database-for-high-scalability/)
