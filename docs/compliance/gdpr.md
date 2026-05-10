# GDPR Compliance Helpers

This template provides building blocks for GDPR compliance — not a certification. Use these helpers as the foundation; your legal team must confirm which Articles apply to your specific use case and jurisdiction.

## Key concepts

| GDPR Article | What it requires | Template helper |
|---|---|---|
| Art. 15 — Right of access | User can request all their data | `GET /api/v1/users/me/export` |
| Art. 17 — Right to erasure | User can request deletion | `DELETE /api/v1/users/{id}/erase` |
| Art. 17 + retention | Erase PII but keep audit trail | `POST /api/v1/users/{id}/pseudonymize` |
| Art. 20 — Data portability | Provide data in machine-readable format | Same export endpoint, returns JSON |

## Data export

An authenticated user can export all their data:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/users/me/export
```

Response structure:

```json
{
  "exported_at": "2026-05-05T12:00:00+00:00",
  "user_id": "abc123",
  "profile": { "username": "...", "email": "...", "phone_number": "...", "role": "..." },
  "api_keys": [...],
  "oauth_accounts": [...],
  "roles": [...],
  "audit_logs": [...]
}
```

### Adding new tables to the export

Edit `app/services/gdpr_service.py::export_user_data`. Add a query for each new table and include the results in the returned dict. This is the single authoritative list of what constitutes a user's data.

## Pseudonymization vs. hard deletion

**When to pseudonymize:**
- You have audit, compliance, or financial records that must be retained.
- GDPR Art. 17(3) exemptions apply (legal obligation, public interest).
- You need referential integrity (other tables FK into the user row).

**When to hard-delete:**
- No retention obligation exists.
- Simpler erasure is preferable.
- Call pseudonymize first to strip PII from audit logs, then hard-delete.

### Pseudonymization mechanics

```
pseudonym = "deleted-" + SHA256("{user_id}:{field_name}:{SECRET_KEY}")[:16]
```

The pseudonym is deterministic (same input → same output) but non-reversible without the SECRET_KEY. Fields registered via `@mark_pii` are replaced:

```python
# app/models/user.py
@mark_pii("email", "phone_number")
class User(Base, SoftDeleteMixin):
    ...
```

After pseudonymization the user row's `deleted_at` is set so soft-delete queries exclude it automatically.

### Endpoints

```bash
# Pseudonymize (admin only) — keeps audit trail, strips PII
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/v1/users/{user_id}/pseudonymize

# Hard delete (admin only) — removes user row + keys + OAuth accounts + roles
curl -X DELETE -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/v1/users/{user_id}/erase
```

## PII field tagging

Mark PII fields on SQLAlchemy models using the `@mark_pii` decorator:

```python
from app.core.pii import mark_pii

@mark_pii("email", "phone_number", "full_name")
class Employee(Base):
    ...
```

The `gdpr_service.pseudonymize_user()` reads this registry at runtime and pseudonymizes all registered fields across all registered models. You do not need to modify the GDPR service when adding new models — just add the decorator.

## Limitations

This template does not:

- Implement GDPR consent management (cookie banners, consent records)
- Implement DSAR (Data Subject Access Request) workflow management
- Provide cross-service data export (only this application's own database)
- Handle third-party data processors (analytics, email providers)

For cross-service GDPR, each service must expose its own export and erasure endpoints, and a central orchestrator must call all of them.
