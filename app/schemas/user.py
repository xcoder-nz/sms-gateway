from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import normalize_phone


class UserRole(str, Enum):
    buyer = "buyer"
    merchant = "merchant"
    admin = "admin"


class UserStatus(str, Enum):
    active = "active"
    blocked = "blocked"


class UserCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=120)
    phone_number: str
    role: UserRole
    status: UserStatus = UserStatus.active
    pin: str = Field(min_length=4, max_length=8)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    role: UserRole | None = None
    status: UserStatus | None = None


class UserResponse(BaseModel):
    id: int
    full_name: str
    phone_number: str
    role: UserRole
    status: UserStatus
