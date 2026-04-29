from uuid import uuid4

from fastapi import APIRouter, Depends
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.api.schemas import MerchantCreate, MerchantOut
from app.db import get_db
from app.models import MerchantProfile, User, Wallet

router = APIRouter(prefix="/api/merchants", tags=["merchants"])
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("", response_model=list[MerchantOut])
def list_merchants(db: Session = Depends(get_db)) -> list[MerchantOut]:
    merchants = db.query(MerchantProfile).order_by(MerchantProfile.id.asc()).all()
    return [MerchantOut(id=m.id, merchant_code=m.merchant_code, display_name=m.display_name, receipt_phone_number=m.receipt_phone_number) for m in merchants]


@router.post("", response_model=MerchantOut)
def create_merchant(payload: MerchantCreate, db: Session = Depends(get_db)) -> MerchantOut:
    user = User(full_name=payload.full_name, phone_number=payload.phone_number, pin_hash=pwd.hash(payload.pin), role="merchant", status="active")
    db.add(user)
    db.commit(); db.refresh(user)
    db.add(Wallet(user_id=user.id, currency="AFN", balance=0, wallet_status="active"))
    merchant = MerchantProfile(user_id=user.id, merchant_code=f"M-{str(uuid4())[:8]}", display_name=payload.display_name, receipt_phone_number=payload.phone_number)
    db.add(merchant)
    db.commit(); db.refresh(merchant)
    return MerchantOut(id=merchant.id, merchant_code=merchant.merchant_code, display_name=merchant.display_name, receipt_phone_number=merchant.receipt_phone_number)
