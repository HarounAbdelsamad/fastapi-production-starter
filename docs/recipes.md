# Recipes

Short "how do I add X?" walkthroughs for the most common extension tasks.

---

## Add a new entity

**1. Create the model** (`app/models/my_entity.py`):

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class MyEntity(Base):
    __tablename__ = "my_entities"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    tenant_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
```

**2. Register in `app/models/__init__.py`:**

```python
from app.models.my_entity import MyEntity

__all__ = [..., "MyEntity"]
```

**3. Generate a migration:**

```bash
make migrate-new msg="add my_entities table"
make migrate
```

**4. Add a service** (`app/services/my_service.py`) and router (`app/routers/my_router.py`), then register the router in `app/main.py`.

---

## Add a new role

Roles are stored in the `roles` table.  Create one via the admin API or the CLI:

```bash
curl -X POST http://localhost:8000/api/v1/roles/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"name": "billing-manager", "description": "Manages billing resources"}'
```

Protect an endpoint with the role:

```python
from app.core.permissions import require_role

@router.get("/billing/invoices")
async def list_invoices(_: User = Depends(require_role("billing-manager"))):
    ...
```

---

## Add a new migration

```bash
# 1. Autogenerate from model changes
make migrate-new msg="add phone_verified column to users"

# 2. Review the generated file in alembic/versions/
# 3. Apply
make migrate

# Roll back one step
alembic downgrade -1
```

For zero-downtime column additions see
[zero-downtime migrations](migrations/zero-downtime.md).

---

## Add an OAuth provider

Google and GitHub are pre-wired.  To add another provider that follows OAuth 2.0:

1. Add a `OAuthProvider` implementation in `app/core/oauth.py` following the
   `GoogleOAuthProvider` pattern.
2. Add the client ID / secret settings to `Settings` in `app/core/config.py`.
3. Register the callback route in `app/routers/oauth.py`.

---

## Add a new IdP for SAML

1. Follow the [SAML setup guide](identity/saml-setup.md) to configure the new IdP.
2. Add IdP metadata to your `.env` (`SAML_IDP_ENTITY_ID`, `SAML_IDP_SSO_URL`,
   `SAML_IDP_CERT`).
3. Export your SP metadata from `/api/v1/auth/saml/metadata` and register it with
   the IdP.

---

## Add a dependency (third-party library)

```bash
uv add some-library
# or for a dev-only dep:
uv add --dev some-library
```

Always run `make test` after adding dependencies to catch incompatibilities before they
land in CI.

---

## Add a new feature flag

Feature flags are runtime-toggled (no restart needed):

```bash
# Create / enable via admin API
curl -X PUT http://localhost:8000/api/v1/admin/features/my-new-feature \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"enabled": false, "description": "New checkout flow — 0% rollout"}'
```

Guard an endpoint:

```python
from app.core.feature_flags import require_feature

@router.get("/checkout/v2")
async def new_checkout(_: bool = Depends(require_feature("my-new-feature"))):
    ...
```

Enable for a specific user without touching the global flag:

```bash
curl -X PUT http://localhost:8000/api/v1/admin/features/my-new-feature/overrides/user/user-abc123 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"enabled": true}'
```

---

## Add PII tagging to a new model

```python
from app.core.pii import mark_pii

@mark_pii("ssn", "date_of_birth")
class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"
    ...
```

The `pseudonymize_user` service will now automatically overwrite these fields when a
GDPR erasure request comes in.

---

## Add a webhook event

After any service action, fire an event to all registered webhook endpoints:

```python
from app.services import webhook_service

# Inside a route or service, after committing:
await webhook_service.dispatch_event(db, "order.placed", {
    "order_id": order.id,
    "user_id": user.user_id,
    "total": order.total,
})
```

Subscribers receive a signed POST with `X-Webhook-Signature: sha256=<hex>`.

---

## Add a background task

Define the task in `app/tasks/`:

```python
# app/tasks/report_tasks.py
from app.worker import celery_app

@celery_app.task(name="tasks.generate_report")
def generate_report(report_id: str) -> None:
    ...  # fetch data, write file, send notification
```

Enqueue it from a service:

```python
from app.core.jobs import get_job_queue

queue = get_job_queue()
queue.enqueue("tasks.generate_report", report_id=report.id)
# Delayed:
queue.enqueue_in(300, "tasks.generate_report", report_id=report.id)
```
