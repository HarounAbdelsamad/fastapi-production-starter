"""Service-to-service (S2S) authentication via HMAC-signed requests.

Each service shares a secret with this API. Requests are signed with:

    message = "{METHOD}\\n{PATH}\\n{TIMESTAMP}\\n{NONCE}"
    if body: message += "\\n" + sha256(body).hexdigest()
    signature = hmac_sha256(secret, message).hexdigest()

Required request headers:
    X-Service-ID     — identifies the calling service (matches key in S2S_SERVICES)
    X-Timestamp      — Unix timestamp (seconds); request rejected if > 300s old
    X-Nonce          — Random value; prevents replay within the time window
    X-Signature      — HMAC-SHA256 hex digest of the canonical message

Enable via ``S2S_ENABLED=true`` and ``S2S_SERVICES={"svc":"secret"}`` in config.

See docs/identity/s2s-auth.md for a full integration guide.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from collections import defaultdict
from threading import Lock

from fastapi import Depends, HTTPException, Request, status

from app.core.config import get_settings

_TIMESTAMP_TOLERANCE = 300  # seconds

# In-memory nonce store: {service_id: {nonce: expiry_ts}}
# In production, swap for Redis SETEX for multi-instance deployments.
_nonces: dict[str, dict[str, float]] = defaultdict(dict)
_nonce_lock = Lock()


def sign_request(
    *,
    method: str,
    path: str,
    body: bytes = b"",
    service_id: str,
    secret: str,
) -> dict[str, str]:
    """Generate the signed-request headers for an outgoing call.

    Example (httpx)::

        headers = sign_request(method="POST", path="/api/v1/tasks",
                                body=json_body, service_id="analytics", secret=MY_SECRET)
        httpx.post(url, headers=headers, content=json_body)
    """
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    message = _canonical_message(
        method=method, path=path, timestamp=timestamp, nonce=nonce, body=body
    )
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return {
        "X-Service-ID": service_id,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
    }


def _canonical_message(*, method: str, path: str, timestamp: str, nonce: str, body: bytes) -> str:
    msg = f"{method.upper()}\n{path}\n{timestamp}\n{nonce}"
    if body:
        msg += "\n" + hashlib.sha256(body).hexdigest()
    return msg


def _evict_expired_nonces(service_id: str, now: float) -> None:
    expired = [n for n, exp in _nonces[service_id].items() if exp < now]
    for n in expired:
        del _nonces[service_id][n]


async def verify_s2s_signature(request: Request) -> str:
    """FastAPI dependency that validates an incoming signed request.

    Returns the ``service_id`` if valid, raises HTTP 401 otherwise.
    """
    cfg = get_settings()
    if not cfg.S2S_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S2S authentication is not enabled",
        )

    service_id = request.headers.get("X-Service-ID", "")
    timestamp_str = request.headers.get("X-Timestamp", "")
    nonce = request.headers.get("X-Nonce", "")
    signature = request.headers.get("X-Signature", "")

    if not all([service_id, timestamp_str, nonce, signature]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing S2S headers")

    # Parse and validate timestamp
    try:
        timestamp = int(timestamp_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid timestamp")

    now = time.time()
    if abs(now - timestamp) > _TIMESTAMP_TOLERANCE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Request timestamp too old or in future",
        )

    # Replay protection
    with _nonce_lock:
        _evict_expired_nonces(service_id, now)
        if nonce in _nonces[service_id]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Nonce already used"
            )
        _nonces[service_id][nonce] = now + _TIMESTAMP_TOLERANCE

    # Lookup service secret
    try:
        services: dict[str, str] = json.loads(cfg.S2S_SERVICES) if cfg.S2S_SERVICES else {}
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="S2S_SERVICES misconfigured",
        )

    secret = services.get(service_id)
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown service ID"
        )

    # Verify signature
    body = await request.body()
    expected = _canonical_message(
        method=request.method,
        path=request.url.path,
        timestamp=timestamp_str,
        nonce=nonce,
        body=body,
    )
    expected_sig = hmac.new(secret.encode(), expected.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid S2S signature"
        )

    return service_id


# Convenience dependency alias
S2SAuth = Depends(verify_s2s_signature)
