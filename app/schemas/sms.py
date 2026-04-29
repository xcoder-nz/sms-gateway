from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import normalize_phone


class InboundSMSRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_number: str
    to_number: str = Field(default="DEMO-SHORTCODE")
    body: str = Field(min_length=1, max_length=500)

    @field_validator("from_number", "to_number")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if value == "DEMO-SHORTCODE":
            return value
        return normalize_phone(value)


class SendSMSRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to_number: str
    body: str = Field(min_length=1, max_length=500)

    @field_validator("to_number")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_phone(value)
