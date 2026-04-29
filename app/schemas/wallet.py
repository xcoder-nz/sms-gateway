from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import normalize_phone


class WalletAdjustmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone_number: str
    amount: int = Field(gt=0)
    reason: str = Field(min_length=2, max_length=140)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)


class WalletTransferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_phone: str
    to_phone: str
    amount: int = Field(gt=0)

    @field_validator("from_phone", "to_phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)
