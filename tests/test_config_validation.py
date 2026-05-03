"""Tests for Settings.validate_config() and migration helper utilities."""

import pytest

from app.core.config import Settings
from app.db.migration_helpers import BackfillProgress, expand_contract_checklist


# ---------------------------------------------------------------------------
# Settings.validate_config
# ---------------------------------------------------------------------------


class TestValidateConfig:
    def _make_settings(self, **overrides) -> Settings:
        """Build a Settings instance with test-safe defaults."""
        base = {
            "APP_ENV": "development",
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "SECRET_KEY": "a" * 64,
        }
        base.update(overrides)
        return Settings(**base)

    def test_clean_config_returns_no_errors(self):
        s = self._make_settings()
        assert s.validate_config() == []

    def test_production_weak_secret_errors(self):
        s = self._make_settings(APP_ENV="production", SECRET_KEY="change-me-to-a-random-secret")
        errors = s.validate_config()
        assert any("SECRET_KEY" in e for e in errors)

    def test_production_short_secret_errors(self):
        s = self._make_settings(APP_ENV="production", SECRET_KEY="short")
        errors = s.validate_config()
        assert any("too short" in e for e in errors)

    def test_production_valid_secret_no_error(self):
        s = self._make_settings(APP_ENV="production", SECRET_KEY="x" * 64)
        errors = s.validate_config()
        assert not any("SECRET_KEY" in e for e in errors)

    def test_cache_enabled_without_redis_url_errors(self):
        s = self._make_settings(CACHE_ENABLED=True, REDIS_URL="")
        errors = s.validate_config()
        assert any("REDIS_URL" in e for e in errors)

    def test_cache_enabled_with_redis_url_no_error(self):
        s = self._make_settings(CACHE_ENABLED=True, REDIS_URL="redis://localhost:6379/0")
        errors = s.validate_config()
        assert not any("REDIS_URL" in e for e in errors)

    def test_celery_enabled_without_broker_errors(self):
        s = self._make_settings(CELERY_ENABLED=True, CELERY_BROKER_URL="")
        errors = s.validate_config()
        assert any("CELERY_BROKER_URL" in e for e in errors)

    def test_s3_backend_missing_keys_errors(self):
        s = self._make_settings(STORAGE_BACKEND="s3", S3_BUCKET_NAME="", S3_REGION="", S3_ACCESS_KEY="", S3_SECRET_KEY="")
        errors = s.validate_config()
        assert len([e for e in errors if "S3_" in e]) >= 1

    def test_s3_backend_all_keys_present_no_error(self):
        s = self._make_settings(
            STORAGE_BACKEND="s3",
            S3_BUCKET_NAME="my-bucket",
            S3_REGION="us-east-1",
            S3_ACCESS_KEY="AKIA...",
            S3_SECRET_KEY="secret",
        )
        errors = s.validate_config()
        assert not any("S3_" in e for e in errors)

    def test_oauth_google_id_without_secret_errors(self):
        s = self._make_settings(OAUTH_GOOGLE_CLIENT_ID="client-id", OAUTH_GOOGLE_CLIENT_SECRET="")
        errors = s.validate_config()
        assert any("OAUTH_GOOGLE_CLIENT_SECRET" in e for e in errors)

    def test_oauth_github_id_without_secret_errors(self):
        s = self._make_settings(OAUTH_GITHUB_CLIENT_ID="client-id", OAUTH_GITHUB_CLIENT_SECRET="")
        errors = s.validate_config()
        assert any("OAUTH_GITHUB_CLIENT_SECRET" in e for e in errors)

    def test_vault_backend_without_token_errors(self):
        s = self._make_settings(SECRETS_BACKEND="vault", VAULT_TOKEN="")
        errors = s.validate_config()
        assert any("VAULT_TOKEN" in e for e in errors)

    def test_aws_backend_without_secret_id_errors(self):
        s = self._make_settings(SECRETS_BACKEND="aws", AWS_SECRET_ID="")
        errors = s.validate_config()
        assert any("AWS_SECRET_ID" in e for e in errors)

    def test_is_properties(self):
        dev = self._make_settings(APP_ENV="development")
        assert dev.is_development
        assert not dev.is_production
        assert not dev.is_testing

        prod = self._make_settings(APP_ENV="production")
        assert prod.is_production

        test = self._make_settings(APP_ENV="testing")
        assert test.is_testing


# ---------------------------------------------------------------------------
# Migration helpers (pure Python, no DB required)
# ---------------------------------------------------------------------------


class TestBackfillProgress:
    def test_pct_zero_rows(self):
        p = BackfillProgress("users", total_rows=0)
        assert p.pct == 100.0

    def test_pct_calculation(self):
        p = BackfillProgress("users", total_rows=1000)
        p.update(250)
        assert p.pct == 25.0

    def test_update_accumulates(self):
        p = BackfillProgress("users", total_rows=100)
        p.update(30)
        p.update(20)
        assert p.processed == 50
        assert p.batches == 2

    def test_elapsed_is_non_negative(self):
        p = BackfillProgress("users", total_rows=100)
        assert p.elapsed_s >= 0.0


class TestExpandContractChecklist:
    def test_returns_six_steps(self):
        steps = expand_contract_checklist("phone_number", "phone", "users")
        assert len(steps) == 6

    def test_expand_phase_first(self):
        steps = expand_contract_checklist("phone_number", "phone", "users")
        expand_steps = [s for s in steps if s["phase"] == "expand"]
        assert len(expand_steps) == 3

    def test_contract_phase_last(self):
        steps = expand_contract_checklist("phone_number", "phone", "users")
        contract_steps = [s for s in steps if s["phase"] == "contract"]
        assert len(contract_steps) == 3

    def test_step_numbers_sequential(self):
        steps = expand_contract_checklist("old_col", "new_col", "my_table")
        assert [s["step"] for s in steps] == [1, 2, 3, 4, 5, 6]

    def test_last_step_drops_old_column(self):
        steps = expand_contract_checklist("old_col", "new_col", "my_table")
        last = steps[-1]
        assert last["sql"] is not None
        assert "DROP COLUMN" in last["sql"]
        assert "old_col" in last["sql"]

    def test_first_step_adds_new_column(self):
        steps = expand_contract_checklist("old_col", "new_col", "my_table")
        first = steps[0]
        assert first["sql"] is not None
        assert "ADD COLUMN" in first["sql"]
        assert "new_col" in first["sql"]
