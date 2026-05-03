"""
Pluggable secret backend protocol and built-in implementations.

See docs/adr/004-pluggable-secrets.md for the design rationale.

Usage
-----
The default provider reads from environment variables — identical to the
existing pydantic-settings behaviour. To use a different backend:

    from app.core.secrets import VaultSecretsProvider
    provider = VaultSecretsProvider(addr="https://vault:8200", token="...")
    db_url = provider.get("DATABASE_URL")

For tests, inject a DictSecretsProvider:

    provider = DictSecretsProvider({"DATABASE_URL": "sqlite+aiosqlite:///:memory:"})
    db_url = provider.get("DATABASE_URL")
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SecretsProvider(Protocol):
    """Structural protocol for secret backends.

    Any class that implements `get` and `get_optional` satisfies this protocol
    without inheritance.  This keeps provider implementations decoupled from
    this codebase (teams can define theirs without importing from here).
    """

    def get(self, key: str) -> str:
        """Return the secret value for *key*.

        Raises ``KeyError`` if the key is not present.
        """
        ...

    def get_optional(self, key: str, default: str = "") -> str:
        """Return the secret value for *key*, or *default* if absent."""
        ...


# ---------------------------------------------------------------------------
# Built-in: environment (default)
# ---------------------------------------------------------------------------


class EnvSecretsProvider:
    """Reads secrets from ``os.environ``.

    This is the zero-dependency default.  It is equivalent to the way
    pydantic-settings reads configuration, but surfaced as a provider so that
    application code calls ``provider.get("KEY")`` rather than
    ``os.environ["KEY"]`` directly.  Swap it for another backend without
    changing any call sites.
    """

    def get(self, key: str) -> str:
        value = os.environ.get(key)
        if value is None:
            raise KeyError(f"Secret '{key}' not found in environment")
        return value

    def get_optional(self, key: str, default: str = "") -> str:
        return os.environ.get(key, default)


# ---------------------------------------------------------------------------
# Built-in: dict (testing)
# ---------------------------------------------------------------------------


class DictSecretsProvider:
    """Dict-backed provider for unit tests.

    Allows injecting arbitrary secrets without touching the environment:

        provider = DictSecretsProvider({
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/test",
        })
        db_url = provider.get("DATABASE_URL")
    """

    def __init__(self, data: dict[str, str]) -> None:
        self._data = dict(data)

    def get(self, key: str) -> str:
        if key not in self._data:
            raise KeyError(f"Secret '{key}' not found in DictSecretsProvider")
        return self._data[key]

    def get_optional(self, key: str, default: str = "") -> str:
        return self._data.get(key, default)


# ---------------------------------------------------------------------------
# Skeleton: HashiCorp Vault
# ---------------------------------------------------------------------------


class VaultSecretsProvider:
    """Fetches secrets from HashiCorp Vault KV v2.

    Requires: ``pip install hvac``

    This is a skeleton implementation.  Teams adopting it should:
    1. Add ``hvac`` to their dependencies.
    2. Integration-test against their own Vault instance.
    3. Implement AppRole auth for production (see the hvac docs).

    Not tested in this template's CI (would require a live Vault instance).

    Args:
        addr:       Vault server address (e.g. ``https://vault.example.com:8200``).
                    Defaults to the ``VAULT_ADDR`` environment variable.
        token:      Vault token for token-based auth.
                    Defaults to the ``VAULT_TOKEN`` environment variable.
        mount:      KV v2 mount path.  Defaults to ``"secret"``.
        path:       KV v2 path prefix for secrets.  Defaults to ``"app"``.
        cache_ttl:  Seconds to cache fetched secrets.  Defaults to 300.
    """

    def __init__(
        self,
        addr: str | None = None,
        token: str | None = None,
        mount: str = "secret",
        path: str = "app",
        cache_ttl: int = 300,
    ) -> None:
        try:
            import hvac  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "VaultSecretsProvider requires the 'hvac' package. "
                "Install it with: pip install hvac"
            ) from exc

        self._mount = mount
        self._path = path
        self._cache_ttl = cache_ttl
        self._cache: dict[str, tuple[str, float]] = {}

        vault_addr = addr or os.environ.get("VAULT_ADDR", "http://localhost:8200")
        vault_token = token or os.environ.get("VAULT_TOKEN", "")

        self._client = hvac.Client(url=vault_addr, token=vault_token)

    def _fetch(self, key: str) -> str | None:
        import time

        cached = self._cache.get(key)
        if cached and (time.time() - cached[1]) < self._cache_ttl:
            return cached[0]

        response = self._client.secrets.kv.v2.read_secret_version(
            path=self._path,
            mount_point=self._mount,
        )
        data: dict[str, str] = response["data"]["data"]
        now = __import__("time").time()
        for k, v in data.items():
            self._cache[k] = (v, now)
        return data.get(key)

    def get(self, key: str) -> str:
        value = self._fetch(key)
        if value is None:
            raise KeyError(f"Secret '{key}' not found in Vault at {self._path}")
        return value

    def get_optional(self, key: str, default: str = "") -> str:
        try:
            value = self._fetch(key)
            return value if value is not None else default
        except Exception:
            return default


# ---------------------------------------------------------------------------
# Skeleton: AWS Secrets Manager
# ---------------------------------------------------------------------------


class AWSSecretsManagerProvider:
    """Fetches secrets from AWS Secrets Manager.

    Requires: ``pip install boto3``

    This is a skeleton implementation.  Teams adopting it should:
    1. Add ``boto3`` to their dependencies.
    2. Use IAM role auth when running on EC2/ECS/Lambda (no credentials needed).
    3. Integration-test against their own AWS account.

    Not tested in this template's CI (would require AWS credentials).

    Args:
        region:     AWS region.  Defaults to the ``AWS_REGION`` or
                    ``AWS_DEFAULT_REGION`` environment variable.
        secret_id:  The ARN or name of the Secrets Manager secret that
                    contains a JSON object with key→value pairs.
        cache_ttl:  Seconds to cache the fetched secret.  Defaults to 300.
    """

    def __init__(
        self,
        secret_id: str,
        region: str | None = None,
        cache_ttl: int = 300,
    ) -> None:
        try:
            import boto3  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "AWSSecretsManagerProvider requires the 'boto3' package. "
                "Install it with: pip install boto3"
            ) from exc

        self._secret_id = secret_id
        self._cache_ttl = cache_ttl
        self._cache: dict[str, str] | None = None
        self._cache_time: float = 0.0

        aws_region = region or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        self._client = boto3.client("secretsmanager", region_name=aws_region)

    def _fetch_all(self) -> dict[str, str]:
        import json
        import time

        if self._cache is not None and (time.time() - self._cache_time) < self._cache_ttl:
            return self._cache

        response = self._client.get_secret_value(SecretId=self._secret_id)
        secret_string = response.get("SecretString", "{}")
        self._cache = json.loads(secret_string)
        self._cache_time = time.time()
        return self._cache  # type: ignore[return-value]

    def get(self, key: str) -> str:
        data = self._fetch_all()
        if key not in data:
            raise KeyError(
                f"Secret '{key}' not found in AWS Secrets Manager secret '{self._secret_id}'"
            )
        return data[key]

    def get_optional(self, key: str, default: str = "") -> str:
        try:
            return self._fetch_all().get(key, default)
        except Exception:
            return default


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_secrets_provider(backend: str = "env") -> SecretsProvider:
    """Return a provider instance for the given backend name.

    Valid values for *backend*: ``"env"`` (default), ``"vault"``, ``"aws"``.

    For Vault and AWS, the provider reads its configuration from environment
    variables (``VAULT_ADDR``, ``VAULT_TOKEN``, ``AWS_REGION``, etc.).  See
    the respective class docstrings for details.
    """
    if backend == "env":
        return EnvSecretsProvider()
    if backend == "vault":
        return VaultSecretsProvider()
    if backend == "aws":
        secret_id = os.environ.get("AWS_SECRET_ID", "")
        if not secret_id:
            raise ValueError(
                "AWS_SECRET_ID environment variable must be set when SECRETS_BACKEND=aws"
            )
        return AWSSecretsManagerProvider(secret_id=secret_id)
    raise ValueError(
        f"Unknown SECRETS_BACKEND '{backend}'. Valid values: env, vault, aws"
    )
