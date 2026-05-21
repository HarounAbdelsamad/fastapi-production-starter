"""Tests for Phase 5 compliance features.

Covers: HMAC audit log signing/verification, GDPR export/pseudonymize/erase,
PII field registry, and rate-limit key functions.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

# ---------------------------------------------------------------------------
# Audit log — HMAC signing
# ---------------------------------------------------------------------------


class TestAuditLogHMAC:
    def _make_log(self, **kwargs):
        from types import SimpleNamespace

        defaults = dict(
            id=str(uuid4()),
            user_id="user-1",
            action="auth.login",
            resource=None,
            detail=None,
            ip_address="127.0.0.1",
            created_at=datetime(2026, 1, 1, 12, 0, 0),
            hmac_signature="",
        )
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    def test_canonical_format(self):
        from app.services.audit_service import _canonical

        log = self._make_log(resource="res", detail="det", ip_address="1.2.3.4")
        canonical = _canonical(log)
        parts = canonical.split("|")
        assert len(parts) == 7
        assert parts[1] == "user-1"
        assert parts[2] == "auth.login"

    def test_canonical_nulls_become_empty_strings(self):
        from app.services.audit_service import _canonical

        log = self._make_log(resource=None, detail=None, ip_address=None)
        canonical = _canonical(log)
        parts = canonical.split("|")
        assert parts[3] == ""
        assert parts[4] == ""
        assert parts[5] == ""

    def test_sign_produces_hex_digest(self):
        from app.services.audit_service import _sign

        log = self._make_log()
        sig = _sign(log, "mysecret")
        assert len(sig) == 64  # SHA-256 hex = 64 chars
        assert all(c in "0123456789abcdef" for c in sig)

    def test_verify_returns_true_for_valid_signature(self):
        from app.services.audit_service import _sign, verify_audit_log

        log = self._make_log()
        log.hmac_signature = _sign(log, "secret123")
        assert verify_audit_log(log, "secret123") is True

    def test_verify_returns_false_for_tampered_row(self):
        from app.services.audit_service import _sign, verify_audit_log

        log = self._make_log()
        log.hmac_signature = _sign(log, "secret123")
        log.action = "TAMPERED"  # mutate after signing
        assert verify_audit_log(log, "secret123") is False

    def test_verify_returns_false_for_wrong_secret(self):
        from app.services.audit_service import _sign, verify_audit_log

        log = self._make_log()
        log.hmac_signature = _sign(log, "correct-secret")
        assert verify_audit_log(log, "wrong-secret") is False

    async def test_log_action_signs_and_commits(self):
        from app.services.audit_service import log_action, verify_audit_log

        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()

        entry = await log_action(
            db,
            user_id="u1",
            action="test.action",
            resource="res:1",
            ip_address="10.0.0.1",
            secret="test-secret",
        )

        assert entry.hmac_signature != ""
        assert verify_audit_log(entry, "test-secret") is True
        db.add.assert_called_once_with(entry)
        db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# PII field registry
# ---------------------------------------------------------------------------


class TestPIIRegistry:
    def test_mark_pii_registers_fields(self):
        from app.core.pii import _PII_REGISTRY, get_pii_fields, mark_pii

        @mark_pii("email", "ssn")
        class FakeModel:
            pass

        fields = get_pii_fields(FakeModel)
        assert "email" in fields
        assert "ssn" in fields

        # Cleanup to avoid polluting registry across tests
        _PII_REGISTRY.pop(FakeModel, None)

    def test_get_pii_fields_returns_empty_for_unregistered(self):
        from app.core.pii import get_pii_fields

        class UnregisteredModel:
            pass

        assert get_pii_fields(UnregisteredModel) == set()

    def test_user_model_has_pii_fields_registered(self):
        from app.core.pii import get_pii_fields
        from app.models.user import User

        fields = get_pii_fields(User)
        assert "email" in fields
        assert "phone_number" in fields

    def test_all_pii_models_returns_dict(self):
        from app.core.pii import all_pii_models
        from app.models.user import User

        registry = all_pii_models()
        assert isinstance(registry, dict)
        assert User in registry


# ---------------------------------------------------------------------------
# GDPR service — pseudonymization logic
# ---------------------------------------------------------------------------


class TestPseudoHash:
    def test_pseudo_is_deterministic(self):
        from app.services.gdpr_service import _pseudo

        r1 = _pseudo("uid", "email", "secret")
        r2 = _pseudo("uid", "email", "secret")
        assert r1 == r2

    def test_pseudo_starts_with_deleted_prefix(self):
        from app.services.gdpr_service import _pseudo

        result = _pseudo("uid", "email", "secret")
        assert result.startswith("deleted-")

    def test_pseudo_differs_by_field(self):
        from app.services.gdpr_service import _pseudo

        r_email = _pseudo("uid", "email", "secret")
        r_phone = _pseudo("uid", "phone_number", "secret")
        assert r_email != r_phone

    def test_pseudo_differs_by_user(self):
        from app.services.gdpr_service import _pseudo

        r1 = _pseudo("user-1", "email", "secret")
        r2 = _pseudo("user-2", "email", "secret")
        assert r1 != r2

    def test_pseudo_differs_by_secret(self):
        from app.services.gdpr_service import _pseudo

        r1 = _pseudo("uid", "email", "secret-a")
        r2 = _pseudo("uid", "email", "secret-b")
        assert r1 != r2


# ---------------------------------------------------------------------------
# Rate-limiting key functions
# ---------------------------------------------------------------------------


class TestRateLimitKeyFunctions:
    def _make_request(self, *, user=None, forwarded=None, client_host="1.2.3.4"):
        req = MagicMock()
        req.state.user = user
        req.headers.get = lambda key, default=None: (
            forwarded if key == "X-Forwarded-For" else default
        )
        req.client.host = client_host
        return req

    def test_get_user_key_returns_user_id_when_present(self):
        from app.core.throttle import get_user_key

        user = MagicMock()
        user.user_id = "abc123"
        req = self._make_request(user=user)
        assert get_user_key(req) == "user:abc123"

    def test_get_user_key_falls_back_to_ip(self):
        from app.core.throttle import get_user_key

        req = self._make_request(user=None)
        assert get_user_key(req) == "1.2.3.4"

    def test_get_tenant_key_returns_tenant_id_when_present(self):
        from app.core.throttle import get_tenant_key

        user = MagicMock()
        user.tenant_id = "tenant-xyz"
        req = self._make_request(user=user)
        assert get_tenant_key(req) == "tenant:tenant-xyz"

    def test_get_tenant_key_falls_back_to_ip(self):
        from app.core.throttle import get_tenant_key

        user = MagicMock()
        user.tenant_id = ""
        req = self._make_request(user=user)
        assert get_tenant_key(req) == "1.2.3.4"

    def test_ip_fallback_uses_x_forwarded_for(self):
        from app.core.throttle import get_user_key

        req = self._make_request(user=None, forwarded="203.0.113.1, 10.0.0.1")
        assert get_user_key(req) == "203.0.113.1"


# ---------------------------------------------------------------------------
# HTTP endpoints — audit log and GDPR (smoke tests via client fixture)
# ---------------------------------------------------------------------------


class TestAuditEndpoints:
    async def test_audit_list_requires_admin(self, client):
        resp = await client.get("/api/v1/audit-logs/")
        # Unauthenticated → 401 or 403
        assert resp.status_code in (401, 403)

    async def test_audit_export_requires_admin(self, client):
        resp = await client.get("/api/v1/audit-logs/export")
        assert resp.status_code in (401, 403)


class TestGDPREndpoints:
    async def test_export_requires_auth(self, client):
        resp = await client.get("/api/v1/users/me/export")
        assert resp.status_code in (401, 403)

    async def test_pseudonymize_requires_admin(self, client):
        resp = await client.post("/api/v1/users/nonexistent/pseudonymize")
        assert resp.status_code in (401, 403)

    async def test_erase_requires_admin(self, client):
        resp = await client.delete("/api/v1/users/nonexistent/erase")
        assert resp.status_code in (401, 403)
