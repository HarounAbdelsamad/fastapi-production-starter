from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: list[str] = []
    expires_days: int | None = Field(default=None, ge=1, le=3650)


class ApiKeyResponse(BaseModel):
    key_id: str
    name: str
    key_prefix: str
    scopes: list[str]
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
    expires_at: datetime | None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, key: object) -> "ApiKeyResponse":
        from app.models.api_key import ApiKey

        assert isinstance(key, ApiKey)
        return cls(
            key_id=key.key_id,
            name=key.name,
            key_prefix=key.key_prefix,
            scopes=key.scopes.split() if key.scopes else [],
            created_at=key.created_at,
            last_used_at=key.last_used_at,
            revoked_at=key.revoked_at,
            expires_at=key.expires_at,
        )


class ApiKeyCreated(ApiKeyResponse):
    """Returned once at creation time — key is never retrievable again."""

    key: str
