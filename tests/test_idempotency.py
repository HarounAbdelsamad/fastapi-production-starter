"""Tests for the idempotency middleware."""


class TestIdempotencyMiddleware:
    async def test_post_without_key_passes_through(self, client):
        resp = await client.post("/api/v1/auth/login", json={"username": "x", "password": "y"})
        # No idempotency key — should process normally (401, not replayed)
        assert "X-Idempotent-Replayed" not in resp.headers

    async def test_get_request_not_guarded(self, client):
        resp = await client.get("/health/live", headers={"Idempotency-Key": "test-key-get"})
        assert "X-Idempotent-Replayed" not in resp.headers

    async def test_duplicate_post_returns_cached_response(self, client):
        idem_key = "unique-idem-key-12345"
        headers = {"Idempotency-Key": idem_key}
        payload = {"username": "idempotent-user", "password": "wrong-password"}

        first = await client.post("/api/v1/auth/login", json=payload, headers=headers)
        second = await client.post("/api/v1/auth/login", json=payload, headers=headers)

        assert first.status_code == second.status_code
        assert second.headers.get("X-Idempotent-Replayed") == "true"

    async def test_different_keys_are_independent(self, client):
        payload = {"username": "u", "password": "p"}
        r1 = await client.post(
            "/api/v1/auth/login", json=payload, headers={"Idempotency-Key": "key-aaa"}
        )
        r2 = await client.post(
            "/api/v1/auth/login", json=payload, headers={"Idempotency-Key": "key-bbb"}
        )
        # Both are first-time requests — neither should be replayed
        assert "X-Idempotent-Replayed" not in r1.headers
        assert "X-Idempotent-Replayed" not in r2.headers


class TestIdempotencyCacheKey:
    def test_cache_key_includes_method_path_and_key(self):
        from app.core.idempotency import _cache_key

        key = _cache_key("my-uuid", "POST", "/api/v1/orders")
        assert "POST" in key
        assert "/api/v1/orders" in key
        assert "my-uuid" in key

    def test_different_paths_produce_different_keys(self):
        from app.core.idempotency import _cache_key

        k1 = _cache_key("same-uuid", "POST", "/api/v1/orders")
        k2 = _cache_key("same-uuid", "POST", "/api/v1/users")
        assert k1 != k2

    def test_different_methods_produce_different_keys(self):
        from app.core.idempotency import _cache_key

        k1 = _cache_key("same-uuid", "POST", "/api/v1/orders")
        k2 = _cache_key("same-uuid", "PATCH", "/api/v1/orders")
        assert k1 != k2
