"""Tests for service-to-service HMAC signed request authentication."""

import json
import time

import pytest

from app.core.s2s import _canonical_message, sign_request

# ── unit tests for signing helpers ─────────────────────────────────────────


class TestSignRequest:
    def test_sign_request_returns_required_headers(self):
        headers = sign_request(
            method="GET", path="/api/v1/tasks", service_id="analytics", secret="mysecret"
        )
        assert "X-Service-ID" in headers
        assert "X-Timestamp" in headers
        assert "X-Nonce" in headers
        assert "X-Signature" in headers

    def test_service_id_matches(self):
        headers = sign_request(method="GET", path="/", service_id="my-svc", secret="s")
        assert headers["X-Service-ID"] == "my-svc"

    def test_timestamp_is_recent(self):
        headers = sign_request(method="GET", path="/", service_id="s", secret="s")
        ts = int(headers["X-Timestamp"])
        assert abs(time.time() - ts) < 5

    def test_different_calls_produce_different_nonces(self):
        h1 = sign_request(method="GET", path="/", service_id="s", secret="s")
        h2 = sign_request(method="GET", path="/", service_id="s", secret="s")
        assert h1["X-Nonce"] != h2["X-Nonce"]

    def test_canonical_message_with_body(self):
        body = b'{"key": "value"}'
        msg = _canonical_message(
            method="POST", path="/api", timestamp="1700000000", nonce="abc123", body=body
        )
        assert "POST" in msg
        assert "/api" in msg
        assert "1700000000" in msg
        assert "abc123" in msg
        # body hash should be present
        import hashlib

        assert hashlib.sha256(body).hexdigest() in msg

    def test_canonical_message_without_body(self):
        msg = _canonical_message(
            method="GET", path="/api", timestamp="1700000000", nonce="abc123", body=b""
        )
        # No SHA hash appended when body is empty
        assert msg == "GET\n/api\n1700000000\nabc123"


# ── integration tests via HTTP ─────────────────────────────────────────────


class TestS2SEndpointDisabled:
    """When S2S_ENABLED=false (default), verify_s2s_signature raises 503."""

    async def test_s2s_disabled_raises_503(self, client):
        from unittest.mock import MagicMock, patch

        from fastapi import HTTPException

        from app.core.s2s import verify_s2s_signature

        mock_request = MagicMock()
        mock_request.headers = {}

        with patch("app.core.s2s.get_settings") as mock_s:
            cfg = MagicMock()
            cfg.S2S_ENABLED = False
            mock_s.return_value = cfg
            with pytest.raises(HTTPException) as exc_info:
                await verify_s2s_signature(mock_request)
            assert exc_info.value.status_code == 503


class TestS2SVerification:
    """Unit tests for signature verification logic."""

    async def test_valid_signature_accepted(self):
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.core.s2s import verify_s2s_signature

        secret = "test-secret-key"
        services = {"test-svc": secret}
        headers_dict = sign_request(
            method="GET", path="/api/v1/test", service_id="test-svc", secret=secret
        )

        mock_request = MagicMock()
        mock_request.headers = {
            "X-Service-ID": headers_dict["X-Service-ID"],
            "X-Timestamp": headers_dict["X-Timestamp"],
            "X-Nonce": headers_dict["X-Nonce"],
            "X-Signature": headers_dict["X-Signature"],
        }
        mock_request.method = "GET"
        mock_request.url.path = "/api/v1/test"
        mock_request.body = AsyncMock(return_value=b"")

        with patch("app.core.s2s.get_settings") as mock_s:
            cfg = MagicMock()
            cfg.S2S_ENABLED = True
            cfg.S2S_SERVICES = json.dumps(services)
            mock_s.return_value = cfg

            # Should not raise
            service_id = await verify_s2s_signature(mock_request)
        assert service_id == "test-svc"

    async def test_wrong_signature_rejected(self):
        from unittest.mock import AsyncMock, MagicMock, patch

        from fastapi import HTTPException

        from app.core.s2s import verify_s2s_signature

        headers_dict = sign_request(
            method="GET", path="/api/v1/test", service_id="test-svc", secret="correct-secret"
        )

        mock_request = MagicMock()
        mock_request.headers = {
            "X-Service-ID": "test-svc",
            "X-Timestamp": headers_dict["X-Timestamp"],
            "X-Nonce": headers_dict["X-Nonce"] + "_tampered",
            "X-Signature": headers_dict["X-Signature"],
        }
        mock_request.method = "GET"
        mock_request.url.path = "/api/v1/test"
        mock_request.body = AsyncMock(return_value=b"")

        with patch("app.core.s2s.get_settings") as mock_s:
            cfg = MagicMock()
            cfg.S2S_ENABLED = True
            cfg.S2S_SERVICES = json.dumps({"test-svc": "correct-secret"})
            mock_s.return_value = cfg

            with pytest.raises(HTTPException) as exc_info:
                await verify_s2s_signature(mock_request)
        assert exc_info.value.status_code == 401

    async def test_expired_timestamp_rejected(self):
        from unittest.mock import MagicMock, patch

        from fastapi import HTTPException

        from app.core.s2s import verify_s2s_signature

        mock_request = MagicMock()
        old_ts = str(int(time.time()) - 400)  # 400s ago, beyond 300s tolerance
        mock_request.headers = {
            "X-Service-ID": "test-svc",
            "X-Timestamp": old_ts,
            "X-Nonce": "some-nonce",
            "X-Signature": "deadbeef",
        }

        with patch("app.core.s2s.get_settings") as mock_s:
            cfg = MagicMock()
            cfg.S2S_ENABLED = True
            cfg.S2S_SERVICES = json.dumps({"test-svc": "secret"})
            mock_s.return_value = cfg

            with pytest.raises(HTTPException) as exc_info:
                await verify_s2s_signature(mock_request)
        assert exc_info.value.status_code == 401
        assert "timestamp" in exc_info.value.detail.lower()
