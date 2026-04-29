from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import normalize_phone


class PaymentRequestStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class PaymentRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    buyer_phone: str
    merchant_phone: str
    amount: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=160)
    status: PaymentRequestStatus = PaymentRequestStatus.pending

    @field_validator("buyer_phone", "merchant_phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)
