from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorResponse(BaseModel):
    ok: bool = False
    error_code: str
    message: str
    details: list[ErrorDetail] = []


class SuccessResponse(BaseModel):
    ok: bool = True
    message: str
    data: dict | None = None
