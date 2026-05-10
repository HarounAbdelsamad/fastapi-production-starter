# Feature Flags (Runtime)

Runtime feature flags are stored in the database and toggled via the admin API — no
restart needed.  They are distinct from env-time booleans like `CACHE_ENABLED` (which
require a restart and control infrastructure) — see ADR-011.

## Evaluation priority

```
user override → tenant override → global flag
```

The most specific context wins.  A flag disabled globally can still be on for a specific
user or tenant.

## Global flags

```http
# List all flags
GET /api/v1/admin/features
Authorization: Bearer <admin-token>

# Enable / create a flag
PUT /api/v1/admin/features/new-checkout-flow
{ "enabled": true, "description": "Redesigned checkout — 10% rollout" }

# Disable a flag
PUT /api/v1/admin/features/new-checkout-flow
{ "enabled": false }
```

## Per-user overrides

```http
# Enable a globally-off flag for one user
PUT /api/v1/admin/features/new-checkout-flow/overrides/user/user-abc123
{ "enabled": true }

# Remove the override (falls back to global)
DELETE /api/v1/admin/features/new-checkout-flow/overrides/user/user-abc123
```

## Per-tenant overrides

```http
PUT /api/v1/admin/features/new-checkout-flow/overrides/tenant/tenant-xyz
{ "enabled": true }

DELETE /api/v1/admin/features/new-checkout-flow/overrides/tenant/tenant-xyz
```

## Guarding an endpoint

```python
from app.core.feature_flags import require_feature

@router.get("/checkout/new")
async def new_checkout(_: bool = Depends(require_feature("new-checkout-flow"))):
    ...
```

Returns 404 when the flag is off (feature appears not to exist to the caller).

## Checking in service code

```python
from app.services.feature_service import is_enabled

# Global check
if await is_enabled(db, "new-checkout-flow"):
    ...

# Per-user check
if await is_enabled(db, "new-checkout-flow", user_id=current_user.user_id):
    ...

# Per-tenant check
if await is_enabled(db, "new-checkout-flow", tenant_id=current_user.tenant_id):
    ...
```

## Caching

When `CACHE_ENABLED=true`, flag lookups are cached in Redis with a 60-second TTL.
Cache is invalidated automatically on every `set_flag` / `set_override` / `delete_override`
write.  Without Redis, every `is_enabled` call hits the database.

```bash
CACHE_ENABLED=true
REDIS_URL=redis://redis:6379/0
```

## Enabling the feature flag system

```bash
FEATURE_FLAGS_ENABLED=true
```

When `false`, `require_feature()` returns 404 for every flag regardless of DB state.
Use this to disable the entire system in environments where you don't want runtime
flag evaluation (e.g., isolated test environments).

## Naming convention

Use `{domain}.{feature}` or `{feature}` in kebab-case:

- `checkout.new-flow`
- `billing.stripe-v2`
- `dark-mode`

Avoid booleans in names (`checkout-enabled`) — a flag being in the table already implies
it is a toggle.
