# ADR-008: Audit Log Signing and Storage Strategy

## Status
Accepted

## Context

Enterprise systems that handle sensitive operations (user management, data access, configuration changes) require a tamper-evident audit trail. The requirements are:

1. **Completeness**: Every material action is logged. Gaps are detectable.
2. **Integrity**: Log entries cannot be modified after the fact without detection.
3. **Availability**: Audit logs are queryable for compliance investigations and user requests.
4. **Exportability**: Logs can be exported for external auditors (CSV, JSONL).
5. **Retention**: Logs are retained for a configurable period. Deletion is explicit and logged.

The challenge is "tamper-evident" — how do we know a log entry hasn't been modified? Options:

1. **No signing**: Trust the database. Insider threat or DB compromise can silently alter records.
2. **HMAC per row**: Each row includes an HMAC signature over its content using a signing key. Modified content is detectable.
3. **Hash chaining**: Each row includes the hash of the previous row (blockchain-style). Any modification breaks the chain from that point forward.
4. **External append-only log**: Write to an external system (S3, a dedicated log service) that provides immutability guarantees.
5. **Postgres-level WAL archiving**: Use database write-ahead log as the audit trail.

## Decision

**HMAC-SHA256 signature on each row, using a configurable signing key. Store audit logs in the same application database. Provide a signature verifier function. Document the limitations explicitly.**

## Reasoning

### HMAC Per Row

Each audit log entry includes a field `signature` computed as:

```python
import hashlib
import hmac

def sign_entry(entry: dict, signing_key: str) -> str:
    payload = canonical_serialize(entry)  # deterministic JSON serialization
    return hmac.new(
        signing_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
```

A verification function checks every row against the current signing key:

```python
def verify_entry(entry: AuditLogEntry, signing_key: str) -> bool:
    expected = sign_entry(entry.to_dict_without_signature(), signing_key)
    return hmac.compare_digest(entry.signature, expected)
```

**Why HMAC over hash chaining**: Hash chaining (each row's hash includes the previous row's hash) provides stronger integrity guarantees — a single modification invalidates all subsequent entries. However:

- Chain verification requires scanning the entire log from the breach point forward — expensive for large audit tables.
- Any failure during a write transaction (crash, rollback) breaks the chain, requiring recovery logic.
- The complexity is not justified for the threat model we're addressing (accidental or low-sophistication tampering). For adversarial, high-sophistication tampering, neither approach is sufficient without an external log service.

HMAC per row is simpler, easier to verify (check any row in isolation), and sufficient for the stated use case.

### Why Not External Append-Only Log

External immutable log services (AWS CloudWatch Logs, Azure Monitor, a write-once S3 bucket) provide stronger guarantees. However:

- **Added operational dependency**: The app can't write audit logs if the external service is unavailable. Acceptable for some architectures, unacceptable for others.
- **Latency**: Network writes for every audited action add latency.
- **Query complexity**: Cross-referencing audit logs with application data requires joins across systems.
- **Cost**: External log storage at high volume adds cost.

The template documents the pattern for exporting to an external log service as a complement to (not replacement for) the DB-side audit log.

### Why Not WAL Archiving

PostgreSQL WAL archiving captures every DB change at the storage level — the strongest possible audit trail. But:

- Postgres-only. This template supports MySQL and SQLite.
- WAL is a binary format — not human-readable without tooling.
- WAL contains all DB operations, not just business-level actions. Separating "user X deleted resource Y" from internal DB housekeeping requires additional tooling.

### Same Database vs Separate Database

Audit logs in the same database as application data is the simplest deployment model. A separate audit database provides stronger isolation (a compromise of the main DB doesn't automatically compromise the audit log). Trade-off:

- Same DB: single connection, transactional writes (audit log entry and business operation in the same transaction — guaranteed atomicity)
- Separate DB: operational complexity, potential for audit log to be out of sync with application state on write failures

Same DB is the default. Teams with strict separation requirements can point the audit log at a different connection string. Documented.

## Implementation

### What Gets Logged

All actions that modify data or access sensitive resources:

- Authentication events (login, logout, failed login, token refresh)
- User management (create, update, delete, role assignment)
- Tenant-scoped data modifications (create, update, delete for configurable entity types)
- Permission changes
- Admin actions
- API key issuance, rotation, revocation
- GDPR export requests and deletion requests
- Configuration changes (feature flag toggles)

What does NOT get logged by default:
- Read-only GET requests (too high volume; available via access logs or OTel if needed)
- Internal health checks
- Background job heartbeats

### Schema

```sql
CREATE TABLE audit_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID REFERENCES tenants(id),
    actor_id    UUID,           -- user or service performing the action
    actor_type  VARCHAR(50),    -- 'user', 'service', 'system'
    action      VARCHAR(100),   -- e.g., 'user.created', 'role.assigned'
    resource    VARCHAR(100),   -- e.g., 'user', 'tenant', 'api_key'
    resource_id VARCHAR(255),   -- the ID of the affected resource
    metadata    JSONB,          -- additional context (old values, new values, IP)
    ip_address  INET,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    signature   VARCHAR(64) NOT NULL  -- HMAC-SHA256 hex digest
);

CREATE INDEX idx_audit_logs_tenant ON audit_logs(tenant_id, created_at DESC);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor_id, created_at DESC);
```

No UPDATE or DELETE permissions are granted to the application user on `audit_logs`. Append-only enforcement is at the application layer (ORM never issues UPDATE/DELETE on this table).

### Key Rotation

When the HMAC signing key rotates:
1. New entries are signed with the new key.
2. Old entries remain valid under the old key.
3. The verifier must support multiple active keys (a key ring).
4. A background task can re-sign old entries with the new key (optional, for single-key verification).

Key rotation procedure is documented.

## Consequences

**Positive:**
- Any modified audit entry is detectable. The verifier function can be run on-demand or as a scheduled job.
- Transactional writes: business operation and audit log entry succeed or fail together.
- No additional infrastructure required.
- Export endpoint (CSV/JSONL) for auditors, GDPR requests, and compliance reviews.

**Negative:**
- HMAC verification requires the signing key. Loss of the signing key means old entries cannot be verified (but they are still readable). Key backup is critical. Documented.
- Append-only is enforced at the application layer only. A DBA with direct DB access can modify rows. For strong immutability, use a separate audit database with restricted access or an external log service. Documented as a limitation.
- High-volume operations (bulk imports, batch jobs) can generate audit log entries at a rate that strains the DB. Batch audit logging is documented as a pattern for high-volume scenarios.

## References

- [HMAC Wikipedia](https://en.wikipedia.org/wiki/HMAC)
- [NIST SP 800-92: Guide to Computer Security Log Management](https://csrc.nist.gov/publications/detail/sp/800-92/final)
