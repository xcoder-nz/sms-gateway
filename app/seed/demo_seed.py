from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import MerchantProfile, User, Wallet

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed_for_session(db: Session, reset: bool = False, pin_hasher=None):
    if reset:
        db.query(MerchantProfile).delete()
        db.query(Wallet).delete()
        db.query(User).delete()
        db.commit()

    if db.query(User).count() > 0:
        return

    hasher = pin_hasher or pwd.hash
    buyer = User(full_name="Buyer One", phone_number="0700123456", national_id="N1", pin_hash=hasher("1234"), role="buyer", status="active")
    merchant = User(full_name="Merchant One", phone_number="0799001100", national_id="N2", pin_hash=hasher("9999"), role="merchant", status="active")
    agent = User(full_name="Agent One", phone_number="0700000001", national_id="N3", pin_hash=hasher("1111"), role="agent", status="active")
    db.add_all([buyer, merchant, agent])
    db.commit()

    for user, bal in [(buyer, 1000), (merchant, 0), (agent, 0)]:
        db.add(Wallet(user_id=user.id, currency="AFN", balance=bal, wallet_status="active"))

    db.add(MerchantProfile(user_id=merchant.id, merchant_code="MRC001", display_name="Merchant One", settlement_mode="simulated", receipt_phone_number=merchant.phone_number))
    db.commit()


def seed():
    db = SessionLocal()
    try:
        seed_for_session(db)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
