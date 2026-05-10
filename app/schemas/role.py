from datetime import datetime

from pydantic import BaseModel, Field


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: str = ""
    parent_role_id: str | None = None


class RoleResponse(BaseModel):
    role_id: str
    name: str
    description: str
    parent_role_id: str | None

    model_config = {"from_attributes": True}


class PermissionResponse(BaseModel):
    permission_id: str
    resource: str
    action: str
    description: str

    model_config = {"from_attributes": True}


class GrantRoleRequest(BaseModel):
    role_id: str


class UserRoleResponse(BaseModel):
    user_id: str
    role_id: str
    role_name: str
    granted_by: str | None
    granted_at: datetime

    model_config = {"from_attributes": True}


class EffectivePermissionsResponse(BaseModel):
    user_id: str
    permissions: list[str]
