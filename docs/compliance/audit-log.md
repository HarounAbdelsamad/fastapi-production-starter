# Audit Log

Every write operation that changes user or system state should emit an audit log entry. The log is append-only, HMAC-signed on write, and exportable as CSV or JSONL.

## Model

| Column | Type | Description |
|---|---|---|
| `id` | UUID | Primary key, generated at write time |
| `user_id` | String | The actor (authenticated user or service account) |
| `action` | String | Verb describing what happened (`login`, `api_key.create`, etc.) |
| `resource` | String? | The target resource, e.g. `user:{id}` or `api_key:{id}` |
| `detail` | String? | Free-form context (sanitised — no PII, no secrets) |
| `ip_address` | String? | Originating IP |
| `created_at` | DateTime | UTC timestamp, set at insert time |
| `hmac_signature` | String | HMAC-SHA256 over the canonical row string |

## Writing

```python
from app.services.audit_service import log_action

await log_action(
    db,
    user_id=current_user.user_id,
    action="api_key.create",
    resource=f"api_key:{key.key_id}",
    ip_address=request.client.host,
)
```

`log_action` signs the row using `SECRET_KEY` before committing. The signature is stored in `hmac_signature`.

## Verifying integrity

```python
from app.services.audit_service import verify_audit_log

ok = verify_audit_log(log_row, settings.SECRET_KEY)
if not ok:
    raise ValueError(f"Audit log row {log_row.id} has been tampered with")
```

The export endpoint includes a `signature_valid` field for each row so consumers can verify the full export offline.

## Canonical message format

The HMAC is computed over:

```
{id}|{user_id}|{action}|{resource or ""}|{detail or ""}|{ip_address or ""}|{created_at.isoformat()}
```

Fields are joined with `|`. Empty nullable fields become empty strings.

## Export

**Requires admin role.**

```bash
# JSONL — includes signature_valid field per row
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/audit-logs/export?format=jsonl" \
  -o audit.jsonl

# CSV
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/audit-logs/export?format=csv" \
  -o audit.csv

# Filter to a single user
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/audit-logs/export?format=jsonl&user_id=abc123" \
  -o user-audit.jsonl
```

## Retention policy

Audit logs are append-only; rows are never updated or deleted by application code. Implement retention at the database level:

```sql
-- Delete logs older than 7 years (adjust to your jurisdiction)
DELETE FROM audit_logs WHERE created_at < NOW() - INTERVAL '7 years';
```

Run this as a scheduled job, not in application code, to maintain separation of concerns.

## Action naming convention

Use `resource.verb` naming to keep actions consistent across the codebase:

| Event | `action` |
|---|---|
| Successful login | `auth.login` |
| Failed login | `auth.login_failed` |
| Password changed | `auth.password_change` |
| API key issued | `api_key.create` |
| API key revoked | `api_key.revoke` |
| API key rotated | `api_key.rotate` |
| Role granted | `role.grant` |
| Role revoked | `role.revoke` |
| User pseudonymized | `gdpr.pseudonymize` |
| User erased | `gdpr.erase` |
| Data exported | `gdpr.export` |
