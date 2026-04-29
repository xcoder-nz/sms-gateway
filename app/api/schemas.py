from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    ok: bool
    mode: str


class SMSOut(BaseModel):
    to_number: str
    body: str


class SMSResult(BaseModel):
    ok: bool
    provider_message_id: str | None = None
    delivery_status: str


class UserCreate(BaseModel):
    full_name: str
    phone_number: str
    pin: str
    role: str = "buyer"
    status: str = "active"


class UserPatch(BaseModel):
    full_name: str | None = None
    status: str | None = None


class UserOut(BaseModel):
    id: int
    full_name: str
    phone_number: str
    role: str
    status: str

    model_config = {"from_attributes": True}


class WalletOut(BaseModel):
    id: int
    user_id: int
    currency: str
    balance: Decimal
    wallet_status: str

    model_config = {"from_attributes": True}


class WalletAction(BaseModel):
    amount: Decimal


class TransactionOut(BaseModel):
    id: int
    reference: str
    type: str
    from_user_id: int | None
    to_user_id: int | None
    merchant_id: int | None
    amount: Decimal
    currency: str
    status: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class MerchantCreate(BaseModel):
    full_name: str
    phone_number: str
    pin: str
    display_name: str


class MerchantOut(BaseModel):
    id: int
    merchant_code: str
    display_name: str
    receipt_phone_number: str


class NetworkSummary(BaseModel):
    users: int
    merchants: int
    wallets: int
    transactions: int


class NetworkFlow(BaseModel):
    reference: str
    amount: Decimal
    from_user_id: int | None
    to_user_id: int | None
    status: str
