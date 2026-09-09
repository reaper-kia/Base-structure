from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.modules.users.domain.enums import Role


class RegisterUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class CreateManagerRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: Role
