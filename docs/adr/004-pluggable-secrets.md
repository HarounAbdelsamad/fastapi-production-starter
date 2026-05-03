# ADR-004: Pluggable Secret Backend Protocol Design

## Status
Accepted

## Context

How application secrets (database passwords, API keys, signing keys) are provided at runtime is an enterprise-critical concern. The naive approach — read everything from environment variables — fails in several real scenarios:

- **Vault-managed secrets**: Many enterprise teams use HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, or GCP Secret Manager. Secrets are fetched at startup or rotated at runtime. They cannot be baked into environment variables without a bootstrapping step.
- **Secret rotation**: A static `.env` file cannot support secrets that rotate. If the DB password changes, the app must restart. This is unacceptable for high-availability systems.
- **Audit requirements**: Some compliance environments require that secret accesses be logged in a central system. You can't audit reads from environment variables.
- **Separation of duties**: In many enterprise environments, the ops team provisions secrets; the dev team cannot see production credentials. A `.env` file approach breaks this model.

The template must work out of the box (no Vault required), but must also provide a clear extension point for teams that use secret backends.

## Decision

**Define a `SecretsProvider` protocol. Implement `EnvSecretsProvider` as the default. Ship skeleton implementations for Vault and AWS Secrets Manager. Document the protocol contract so teams can add their own backend in ~50 lines.**

## Protocol Design

```python
from typing import Protocol

class SecretsProvider(Protocol):
    def get(self, key: str) -> str:
        """
        Retrieve a secret by key. Raises KeyError if not found.
        Implementations may cache, lazy-fetch, or rotate transparently.
        """
        ...

    def get_optional(self, key: str, default: str = "") -> str:
        """Return default if key is not present."""
        ...
```

### Why a Protocol, Not an Abstract Base Class

- **No inheritance required**: Teams implementing their own backend don't import from this codebase. Structural subtyping means any class with `get()` and `get_optional()` satisfies the protocol.
- **Easier testing**: Tests can inject a plain dict-backed implementation without subclassing.
- **Lower coupling**: The protocol is a contract, not a dependency. If the codebase changes the ABC, downstream implementations break. Protocols don't have this problem.

## Implementations

### `EnvSecretsProvider` (default)
```python
class EnvSecretsProvider:
    def get(self, key: str) -> str:
        value = os.environ.get(key)
        if value is None:
            raise KeyError(f"Secret '{key}' not found in environment")
        return value

    def get_optional(self, key: str, default: str = "") -> str:
        return os.environ.get(key, default)
```

This is the zero-dependency default. It reads from environment variables, which is how most small deployments and all local dev environments work. No extra setup required.

### `VaultSecretsProvider` (skeleton)

Fetches secrets from HashiCorp Vault's KV v2 engine. Requires `hvac` library. Supports:
- Token-based auth
- AppRole auth (recommended for production)
- Secret caching with TTL
- Vault address and mount path configurable via env

Ships as a skeleton with the extension points documented. Not production-tested as part of this template's CI (would require a Vault instance). Teams adopting it should integration-test against their own Vault.

### `AWSSecretsManagerProvider` (skeleton)

Fetches secrets from AWS Secrets Manager. Requires `boto3`. Supports:
- IAM role auth (recommended for production; no credentials needed when running on EC2/ECS/Lambda)
- Region configurable via env
- Secret caching with configurable TTL

Same caveat: shipped as a skeleton, not tested in CI.

## Integration with Pydantic Settings

The `SecretsProvider` integrates with `pydantic-settings` by injecting secret values before settings validation:

```python
class Settings(BaseSettings):
    database_url: str
    secret_key: str

    @classmethod
    def from_secrets(cls, provider: SecretsProvider) -> "Settings":
        return cls(
            database_url=provider.get("DATABASE_URL"),
            secret_key=provider.get("SECRET_KEY"),
        )
```

This approach keeps Pydantic validation (type checking, constraint validation) while allowing the source of values to vary. The env fallback still works: `EnvSecretsProvider` reads from environment, which is where `pydantic-settings` normally reads from.

## Secret Rotation Pattern

For systems that require zero-downtime secret rotation:

1. The `SecretsProvider` implementation caches secrets with a TTL.
2. On TTL expiry, the provider re-fetches from the backend.
3. Long-lived connections (DB pool) use a connection-level check-and-reconnect pattern on the next use.

The template documents this pattern. Implementing it requires coordination with the provider's rotation mechanism. Not all teams need this; it is documented as an advanced pattern.

## Consequences

**Positive:**
- Zero added dependencies by default. `EnvSecretsProvider` uses only the standard library.
- Teams using Vault or AWS Secrets Manager have a clear, documented extension point. They don't need to fork the template or monkey-patch config.
- The protocol can be tested with a dict-backed mock in unit tests — no real secrets backend needed.
- Pydantic validation still runs after secret resolution. Bad values are caught at startup.

**Negative:**
- Adds a layer of indirection compared to reading directly from `os.environ`. Worth the cost for the extension point, but developers new to the codebase need to understand the flow.
- Vault/AWS skeletons are not tested in CI. Teams adopting them should add their own integration tests. Documented explicitly.
- Secret rotation in DB connection pools requires careful implementation. The template provides the pattern but not the complete implementation for every pool library.

## References

- [HashiCorp Vault KV v2 API](https://developer.hashicorp.com/vault/api-docs/secret/kv/kv-v2)
- [AWS Secrets Manager developer guide](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)
- [pydantic-settings documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [PEP 544 — Protocols](https://peps.python.org/pep-0544/)
