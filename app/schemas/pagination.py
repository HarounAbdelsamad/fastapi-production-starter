from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    skip: int
    limit: int
    has_more: bool
