from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    status: str = "active"


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: str | None = None


class ProjectRead(BaseModel):
    id: int
    tenant_id: str
    owner_id: int
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    assignee_id: int | None = None
    due_at: datetime | None = None


class TaskRead(BaseModel):
    id: int
    project_id: int
    tenant_id: str
    title: str
    done: bool
    assignee_id: int | None
    due_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
