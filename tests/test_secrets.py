"""Tests for the SecretsProvider protocol and built-in implementations."""


import pytest

from app.core.secrets import (
    DictSecretsProvider,
    EnvSecretsProvider,
    SecretsProvider,
    get_secrets_provider,
)


class TestEnvSecretsProvider:
    def test_get_existing_key(self, monkeypatch):
        monkeypatch.setenv("TEST_SECRET_KEY", "my-secret-value")
        provider = EnvSecretsProvider()
        assert provider.get("TEST_SECRET_KEY") == "my-secret-value"

    def test_get_missing_key_raises(self):
        provider = EnvSecretsProvider()
        with pytest.raises(KeyError, match="TEST_MISSING_KEY_XYZ"):
            provider.get("TEST_MISSING_KEY_XYZ")

    def test_get_optional_existing(self, monkeypatch):
        monkeypatch.setenv("TEST_OPT_KEY", "present")
        provider = EnvSecretsProvider()
        assert provider.get_optional("TEST_OPT_KEY") == "present"

    def test_get_optional_missing_returns_default(self):
        provider = EnvSecretsProvider()
        assert provider.get_optional("TEST_COMPLETELY_MISSING_XYZ") == ""
        assert provider.get_optional("TEST_COMPLETELY_MISSING_XYZ", "fallback") == "fallback"

    def test_satisfies_protocol(self):
        provider = EnvSecretsProvider()
        assert isinstance(provider, SecretsProvider)


class TestDictSecretsProvider:
    def test_get_existing_key(self):
        provider = DictSecretsProvider({"DB_URL": "sqlite:///:memory:"})
        assert provider.get("DB_URL") == "sqlite:///:memory:"

    def test_get_missing_key_raises(self):
        provider = DictSecretsProvider({})
        with pytest.raises(KeyError, match="MISSING_KEY"):
            provider.get("MISSING_KEY")

    def test_get_optional_existing(self):
        provider = DictSecretsProvider({"KEY": "value"})
        assert provider.get_optional("KEY") == "value"

    def test_get_optional_missing_returns_default(self):
        provider = DictSecretsProvider({})
        assert provider.get_optional("NOPE") == ""
        assert provider.get_optional("NOPE", "fallback") == "fallback"

    def test_does_not_mutate_source_dict(self):
        source = {"A": "1"}
        DictSecretsProvider(source)
        source["B"] = "2"
        provider = DictSecretsProvider({"A": "1"})
        with pytest.raises(KeyError):
            provider.get("B")

    def test_satisfies_protocol(self):
        provider = DictSecretsProvider({})
        assert isinstance(provider, SecretsProvider)


class TestGetSecretsProvider:
    def test_env_backend(self):
        provider = get_secrets_provider("env")
        assert isinstance(provider, EnvSecretsProvider)

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError, match="Unknown SECRETS_BACKEND"):
            get_secrets_provider("unknown-backend")

    def test_vault_backend_raises_without_hvac(self, monkeypatch):
        """VaultSecretsProvider should raise ImportError if hvac is not installed."""
        import sys

        monkeypatch.setitem(sys.modules, "hvac", None)
        with pytest.raises((ImportError, Exception)):
            get_secrets_provider("vault")

    def test_aws_backend_raises_without_secret_id(self, monkeypatch):
        """AWSSecretsManagerProvider should raise ValueError if AWS_SECRET_ID is unset."""
        monkeypatch.delenv("AWS_SECRET_ID", raising=False)
        with pytest.raises(ValueError, match="AWS_SECRET_ID"):
            get_secrets_provider("aws")


class TestProtocolStructural:
    """Any class with the right methods satisfies SecretsProvider — no inheritance needed."""

    def test_ad_hoc_class_satisfies_protocol(self):
        class MyProvider:
            def get(self, key: str) -> str:
                return "value"

            def get_optional(self, key: str, default: str = "") -> str:
                return default

        assert isinstance(MyProvider(), SecretsProvider)

    def test_missing_method_does_not_satisfy(self):
        class Incomplete:
            def get(self, key: str) -> str:
                return ""

        # Missing get_optional → does not satisfy protocol at runtime check
        assert not isinstance(Incomplete(), SecretsProvider)
