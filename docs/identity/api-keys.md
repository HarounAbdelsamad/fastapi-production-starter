# API Key Authentication

DB-backed API keys replace the static `API_KEYS` list in settings. Keys are scoped, rotatable, and revocable without a restart.

## Key format

```
fpsk_<64-hex-chars>
```

`fpsk` = FastAPI Starter Key prefix. Prefix is indexed for display; the SHA-256 hash is stored — the raw key is **never** recoverable after issuance.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/api-keys` | Issue a new key |
| `GET` | `/api/v1/api-keys` | List keys (no raw values) |
| `DELETE` | `/api/v1/api-keys/{key_id}` | Revoke a key |
| `POST` | `/api/v1/api-keys/{key_id}/rotate` | Revoke + re-issue with same scopes |

## Issue a key

```bash
curl -X POST /api/v1/api-keys \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"name": "ci-pipeline", "scopes": ["users:read"], "expires_days": 90}'
```

Response (key shown **once**):
```json
{
  "key_id": "...",
  "name": "ci-pipeline",
  "key_prefix": "fpsk_a1b2c3",
  "scopes": ["users:read"],
  "key": "fpsk_a1b2c3d4e5f6...",
  "created_at": "2026-05-05T12:00:00",
  "expires_at": "2026-08-03T12:00:00"
}
```

## Use a key

Pass `X-API-Key` on every request:

```bash
curl /api/v1/users/ -H "X-API-Key: fpsk_a1b2c3d4e5f6..."
```

The key resolves to its owner user; the owner's role/permissions apply.

## Scopes

Scopes are advisory strings (`resource:action`) stored on the key. The application can inspect them via `request.state.api_key_scopes` for fine-grained enforcement.

## Rotation

```bash
curl -X POST /api/v1/api-keys/{key_id}/rotate \
  -H "Authorization: Bearer $JWT"
```

The old key is immediately revoked; the response contains the new raw key.

## Backward compatibility

The static `API_KEYS` setting (list of raw key strings) still works for system-level service accounts. DB-backed keys (`fpsk_...`) take precedence in lookup.

## Storage security

- Raw key is generated with `secrets.token_hex(32)` (256-bit entropy)
- SHA-256 of the raw key is stored in the DB
- No bcrypt/Argon2 — API keys are high-entropy by construction, SHA-256 is appropriate
- Never log or store the raw key server-side after issuance
