from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    action: str
    resource: str | None = None
    detail: str | None = None
    ip_address: str | None = None
    created_at: datetime
