# Multi-Tenancy Pattern

This template provides reusable primitives for row-level tenant isolation:

- `app.db.mixins.TenantMixin`
- `app.core.tenant.get_current_tenant`
- `app.db.tenant_filter.tenant_query`

## How to apply

1. Add `TenantMixin` to your domain model.
2. Resolve `tenant_id` in routers/services using `get_current_tenant`.
3. Apply `tenant_query(select(Model), Model, tenant_id)` to all tenant-scoped reads.
4. Always set `tenant_id` on create/update paths.

The default `User` model is intentionally left non-tenant-scoped.
