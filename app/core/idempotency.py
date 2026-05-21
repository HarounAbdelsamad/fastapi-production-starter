"""Idempotency-key middleware.

Clients attach an ``Idempotency-Key: <uuid>`` header to POST / PATCH requests.
The middleware:

1. Checks the key in the store (Redis when ``CACHE_ENABLED=true``, in-process
   dict otherwise).
2. Cache hit  → returns the stored response, adding ``X-Idempotent-Replayed: true``.
3. Cache miss → lets the request through, stores status + body, returns normally.

Keys expire after ``IDEMPOTENCY_TTL`` seconds (default 86 400 = 24 h).
GET / PUT / DELETE are not guarded (GET is safe; PUT / DELETE are idempotent by spec).

See ``docs/operations/idempotency.md`` for the client contract and edge cases.
"""

from __future__ import annotations

import json
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

_GUARDED_METHODS = {"POST", "PATCH"}
_HEADER = "Idempotency-Key"

# In-process fallback (single-instance only; resets on restart).
_local_cache: dict[str, dict[str, Any]] = {}


def _cache_key(key: str, method: str, path: str) -> str:
    return f"idempotency:{method}:{path}:{key}"


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """De-duplicates requests using the ``Idempotency-Key`` header."""

    def __init__(self, app: ASGIApp, ttl: int = 86_400) -> None:
        super().__init__(app)
        self.ttl = ttl

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method not in _GUARDED_METHODS:
            return await call_next(request)

        idem_key = request.headers.get(_HEADER)
        if not idem_key:
            return await call_next(request)

        cache_key = _cache_key(idem_key, request.method, request.url.path)

        stored = await self._get(cache_key)
        if stored is not None:
            return Response(
                content=stored["body"].encode("utf-8", errors="replace"),
                status_code=stored["status"],
                media_type=stored.get("content_type", "application/json"),
                headers={"X-Idempotent-Replayed": "true"},
            )

        response = await call_next(request)

        body_bytes = b""
        async for chunk in response.body_iterator:
            body_bytes += chunk

        await self._set(
            cache_key,
            {
                "status": response.status_code,
                "body": body_bytes.decode("utf-8", errors="replace"),
                "content_type": response.headers.get("content-type", "application/json"),
            },
        )

        return Response(
            content=body_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type"),
        )

    async def _get(self, key: str) -> dict[str, Any] | None:
        try:
            from app.core.cache import get_redis

            redis = await get_redis()
            if redis is not None:
                raw = await redis.get(key)
                if raw:
                    return json.loads(raw)  # type: ignore[return-value]
        except Exception:
            pass
        return _local_cache.get(key)

    async def _set(self, key: str, value: dict[str, Any]) -> None:
        try:
            from app.core.cache import get_redis

            redis = await get_redis()
            if redis is not None:
                await redis.set(key, json.dumps(value), ex=self.ttl)
                return
        except Exception:
            pass
        _local_cache[key] = value
