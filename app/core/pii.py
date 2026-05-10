"""PII field registry.

Mark SQLAlchemy models with @mark_pii("field1", "field2") to register which
columns contain personally identifiable information. The GDPR service uses
this registry to know which fields to pseudonymize on erasure requests.

Usage::

    from app.core.pii import mark_pii

    @mark_pii("email", "phone_number")
    class User(Base, SoftDeleteMixin):
        ...
"""

from __future__ import annotations

_PII_REGISTRY: dict[type, set[str]] = {}


def mark_pii(*field_names: str):
    """Class decorator — registers the named fields as PII for a SQLAlchemy model."""

    def decorator(cls: type) -> type:
        _PII_REGISTRY[cls] = set(field_names)
        return cls

    return decorator


def get_pii_fields(model_class: type) -> set[str]:
    """Return the set of PII field names registered for *model_class*."""
    return _PII_REGISTRY.get(model_class, set())


def all_pii_models() -> dict[type, set[str]]:
    """Return the full registry — used by gdpr_service for batch pseudonymization."""
    return dict(_PII_REGISTRY)
