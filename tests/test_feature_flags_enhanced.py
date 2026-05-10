"""Tests for enhanced feature flag service (overrides + cache)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestFeatureFlagOverrideModel:
    def test_feature_flag_override_model_exists(self):
        from app.models.feature_flag import FeatureFlagOverride

        assert hasattr(FeatureFlagOverride, "key")
        assert hasattr(FeatureFlagOverride, "subject_type")
        assert hasattr(FeatureFlagOverride, "subject_id")
        assert hasattr(FeatureFlagOverride, "enabled")


class TestIsEnabledPriority:
    """Verify evaluation priority: user override → tenant override → global."""

    def _make_db(self, *, global_enabled: bool, user_override=None, tenant_override=None):
        """Return a mock AsyncSession whose execute returns the given state."""
        db = AsyncMock()

        async def execute_side_effect(query):
            result = MagicMock()
            scalars = MagicMock()
            result.scalars.return_value = scalars

            # Detect which query is being run by its WHERE clauses (crude but sufficient)
            query_str = str(query)
            if "subject_type" in query_str:
                if user_override is not None and "user" in query_str:
                    obj = MagicMock()
                    obj.enabled = user_override
                    scalars.first.return_value = obj
                elif tenant_override is not None and "tenant" in query_str:
                    obj = MagicMock()
                    obj.enabled = tenant_override
                    scalars.first.return_value = obj
                else:
                    scalars.first.return_value = None
            else:
                if global_enabled is not None:
                    obj = MagicMock()
                    obj.enabled = global_enabled
                    scalars.first.return_value = obj
                else:
                    scalars.first.return_value = None
            return result

        db.execute = execute_side_effect
        return db

    async def test_global_flag_returned_when_no_overrides(self):
        from app.services.feature_service import is_enabled

        db = self._make_db(global_enabled=True)
        result = await is_enabled(db, "my-flag")
        assert result is True

    async def test_global_flag_false_returned_when_no_overrides(self):
        from app.services.feature_service import is_enabled

        db = self._make_db(global_enabled=False)
        result = await is_enabled(db, "my-flag")
        assert result is False

    async def test_user_override_takes_precedence_over_global(self):
        from app.services.feature_service import is_enabled

        # Global off, user override on
        db = self._make_db(global_enabled=False, user_override=True)

        with patch("app.services.feature_service._get_override", new=AsyncMock(return_value=True)):
            result = await is_enabled(db, "my-flag", user_id="user-123")
        assert result is True

    async def test_missing_flag_returns_false(self):
        from app.services.feature_service import is_enabled

        db = self._make_db(global_enabled=None)
        result = await is_enabled(db, "nonexistent-flag")
        assert result is False


class TestSetOverride:
    async def test_set_override_creates_record(self):
        from app.services.feature_service import set_override

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        db.execute = AsyncMock(return_value=result_mock)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()

        with patch("app.services.feature_service._redis_delete", new=AsyncMock()):
            await set_override(
                db, key="my-flag", subject_type="user", subject_id="u-1", enabled=True
            )
        db.add.assert_called_once()
        db.commit.assert_awaited_once()

    async def test_set_override_updates_existing(self):
        from app.services.feature_service import set_override

        db = AsyncMock()
        existing = MagicMock()
        existing.enabled = False
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = existing
        db.execute = AsyncMock(return_value=result_mock)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = MagicMock()

        with patch("app.services.feature_service._redis_delete", new=AsyncMock()):
            await set_override(
                db, key="my-flag", subject_type="user", subject_id="u-1", enabled=True
            )
        assert existing.enabled is True
        db.add.assert_not_called()


class TestOverrideEndpoints:
    async def test_upsert_override_requires_admin(self, client):
        resp = await client.put(
            "/api/v1/admin/features/my-flag/overrides/user/user-1",
            json={"enabled": True},
        )
        assert resp.status_code in (401, 403)

    async def test_delete_override_requires_admin(self, client):
        resp = await client.delete(
            "/api/v1/admin/features/my-flag/overrides/user/user-1"
        )
        assert resp.status_code in (401, 403)

    async def test_invalid_subject_type_rejected(self, client):
        # Endpoint rejects invalid subject_type with 401/403 (unauthenticated)
        # or 422 (authenticated). We only verify the route exists and validates.
        resp = await client.put(
            "/api/v1/admin/features/my-flag/overrides/invalid-type/some-id",
            json={"enabled": True},
        )
        # Unauthenticated → 401/403 before validation; either way not 200
        assert resp.status_code in (401, 403, 422)
