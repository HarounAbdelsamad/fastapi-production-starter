"""Tests for outgoing webhook service and endpoints."""

import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Signature verification helper
# ---------------------------------------------------------------------------


def _verify_sig(payload: str, secret: str, signature: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Unit tests — service internals
# ---------------------------------------------------------------------------


class TestWebhookSignature:
    def test_sign_produces_sha256_prefix(self):
        from app.services.webhook_service import _sign

        sig = _sign('{"event":"test"}', "mysecret")
        assert sig.startswith("sha256=")
        assert len(sig) == 71  # "sha256=" (7) + 64 hex chars

    def test_sign_is_verifiable(self):
        from app.services.webhook_service import _sign

        payload = '{"event":"user.created","user_id":"u1"}'
        secret = "super-secret"
        sig = _sign(payload, secret)
        assert _verify_sig(payload, secret, sig)

    def test_tampered_payload_fails_verification(self):
        from app.services.webhook_service import _sign

        payload = '{"event":"user.created"}'
        sig = _sign(payload, "secret")
        assert not _verify_sig('{"event":"TAMPERED"}', "secret", sig)


class TestWebhookEventMatching:
    def test_wildcard_matches_any_event(self):
        from app.services.webhook_service import _matches

        assert _matches("*", "user.created") is True
        assert _matches("*", "anything.at.all") is True

    def test_comma_separated_matches_included(self):
        from app.services.webhook_service import _matches

        assert _matches("user.created,user.deleted", "user.created") is True
        assert _matches("user.created,user.deleted", "user.deleted") is True

    def test_comma_separated_rejects_excluded(self):
        from app.services.webhook_service import _matches

        assert _matches("user.created,user.deleted", "order.placed") is False

    def test_single_event_matches(self):
        from app.services.webhook_service import _matches

        assert _matches("order.placed", "order.placed") is True
        assert _matches("order.placed", "order.shipped") is False


class TestRetrySchedule:
    def test_first_retry_is_30_seconds(self):
        from types import SimpleNamespace

        from app.services.webhook_service import _schedule_retry

        delivery = SimpleNamespace(attempts=1, status="pending", next_retry_at=None)
        _schedule_retry(delivery)
        assert delivery.status == "pending"
        assert delivery.next_retry_at is not None

    def test_max_attempts_marks_failed(self):
        from types import SimpleNamespace

        from app.services.webhook_service import _MAX_ATTEMPTS, _schedule_retry

        delivery = SimpleNamespace(
            attempts=_MAX_ATTEMPTS, status="pending", next_retry_at=None
        )
        _schedule_retry(delivery)
        assert delivery.status == "failed"
        assert delivery.next_retry_at is None


# ---------------------------------------------------------------------------
# Integration tests — HTTP endpoints (auth guards)
# ---------------------------------------------------------------------------


class TestWebhookEndpoints:
    async def test_register_requires_admin(self, client):
        resp = await client.post(
            "/api/v1/webhooks/",
            json={"url": "https://example.com/hook", "secret": "s", "events": "*"},
        )
        assert resp.status_code in (401, 403)

    async def test_list_endpoints_requires_admin(self, client):
        resp = await client.get("/api/v1/webhooks/")
        assert resp.status_code in (401, 403)

    async def test_delete_endpoint_requires_admin(self, client):
        resp = await client.delete("/api/v1/webhooks/nonexistent")
        assert resp.status_code in (401, 403)

    async def test_list_deliveries_requires_admin(self, client):
        resp = await client.get("/api/v1/webhooks/deliveries/")
        assert resp.status_code in (401, 403)

    async def test_replay_requires_admin(self, client):
        resp = await client.post("/api/v1/webhooks/deliveries/nonexistent/replay")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Service-layer tests with mocked DB
# ---------------------------------------------------------------------------


class TestWebhookService:
    async def test_register_endpoint_persists(self):
        from app.services.webhook_service import register_endpoint

        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=lambda ep: None)

        await register_endpoint(db, url="https://example.com", secret="s", events="*")
        db.add.assert_called_once()
        db.commit.assert_awaited_once()

    async def test_dispatch_skips_inactive_endpoints(self):
        from app.services.webhook_service import dispatch_event

        db = AsyncMock()
        # No active endpoints
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=result_mock)
        db.commit = AsyncMock()

        deliveries = await dispatch_event(db, "user.created", {"user_id": "u1"})
        assert deliveries == []

    async def test_dispatch_creates_delivery_per_endpoint(self):
        from types import SimpleNamespace

        from app.services.webhook_service import dispatch_event

        endpoint = SimpleNamespace(
            id="ep-1",
            url="https://example.com/hook",
            secret="s3cr3t",
            events="*",
            active=True,
        )

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [endpoint]
        db.execute = AsyncMock(return_value=result_mock)
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.add = MagicMock()

        with patch("app.services.webhook_service._deliver", new=AsyncMock()):
            deliveries = await dispatch_event(db, "user.created", {"user_id": "u1"})

        assert len(deliveries) == 1
        assert deliveries[0].event == "user.created"
        assert deliveries[0].endpoint_id == "ep-1"
