from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    user_id: str
    username: str
    password: str
    email: str
    phone_number: str | None = None
    role: str = "user"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: str
    email: str
    phone_number: str | None = None
    role: str


class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    email: str | None = None
    phone_number: str | None = None
