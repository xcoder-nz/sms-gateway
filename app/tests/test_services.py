from decimal import Decimal

from app.adapters.sms.mock import MockSMSAdapter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import SMSMessage, Transaction, User, Wallet
from app.services.notification_service import NotificationService
from app.services.transaction_service import TransactionService
from app.services.wallet_service import WalletService



def build_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def seed_users(db):
    buyer = User(full_name="Buyer One", phone_number="0700000001", national_id="N1", pin_hash="1234", role="buyer", status="active")
    merchant = User(full_name="Merchant One", phone_number="0700000002", national_id="N2", pin_hash="9999", role="merchant", status="active")
    db.add_all([buyer, merchant])
    db.commit()
    db.refresh(buyer)
    db.refresh(merchant)
    db.add_all([
        Wallet(user_id=buyer.id, balance=Decimal("100.00"), currency="AFN"),
        Wallet(user_id=merchant.id, balance=Decimal("20.00"), currency="AFN"),
    ])
    db.commit()
    return buyer, merchant


def test_wallet_service_get_balance_success():
    db = build_session()
    buyer, _ = seed_users(db)

    result = WalletService(db).get_user_balance(buyer)

    assert result.balance == Decimal("100.00")
    assert result.currency == "AFN"


def test_wallet_service_get_balance_missing_wallet():
    db = build_session()
    user = User(full_name="No Wallet", phone_number="0700000003", national_id="N3", pin_hash="1234", role="buyer", status="active")
    db.add(user)
    db.commit()
    db.refresh(user)

    try:
        WalletService(db).get_user_balance(user)
        assert False
    except ValueError as exc:
        assert str(exc) == "Wallet not found"


def test_transaction_service_pay_success():
    db = build_session()
    buyer, merchant = seed_users(db)

    result = TransactionService(db).pay(buyer, merchant.phone_number, Decimal("25.00"), "1234")

    assert result.status == "completed"
    buyer_wallet = db.query(Wallet).filter(Wallet.user_id == buyer.id).first()
    merchant_wallet = db.query(Wallet).filter(Wallet.user_id == merchant.id).first()
    assert buyer_wallet.balance == Decimal("75.00")
    assert merchant_wallet.balance == Decimal("45.00")


def test_transaction_service_pay_rejected_invalid_pin():
    db = build_session()
    buyer, merchant = seed_users(db)

    result = TransactionService(db).pay(buyer, merchant.phone_number, Decimal("25.00"), "0000")

    assert result.status == "rejected"
    assert result.reason == "invalid_pin"


def test_transaction_service_pay_rejected_insufficient_balance():
    db = build_session()
    buyer, merchant = seed_users(db)

    result = TransactionService(db).pay(buyer, merchant.phone_number, Decimal("500.00"), "1234")

    assert result.status == "rejected"
    assert result.reason == "insufficient_balance"


def test_transaction_service_pay_rejected_invalid_amount():
    db = build_session()
    buyer, merchant = seed_users(db)

    result = TransactionService(db).pay(buyer, merchant.phone_number, Decimal("0"), "1234")

    assert result.status == "rejected"
    assert result.reason == "invalid_amount"


def test_transaction_service_balance_inquiry_completed():
    db = build_session()
    buyer, _ = seed_users(db)

    result = TransactionService(db).create_balance_inquiry(buyer)

    assert result.status == "completed"
    tx = db.query(Transaction).filter(Transaction.id == result.transaction_id).first()
    assert tx.type == "balance_inquiry"


def test_transaction_service_cashin_and_cashout_rejected_not_implemented():
    db = build_session()
    buyer, _ = seed_users(db)
    service = TransactionService(db)

    cashin_result = service.cashin(buyer, "0700000001", Decimal("20"))
    cashout_result = service.cashout(buyer, "0700000001", Decimal("20"))

    assert cashin_result.status == "rejected"
    assert cashin_result.reason == "not_implemented"
    assert cashout_result.status == "rejected"
    assert cashout_result.reason == "not_implemented"


def test_notification_service_send_sms_persists_message():
    db = build_session()
    service = NotificationService(db, adapter=MockSMSAdapter())

    provider_message_id = service.send_sms("0700000009", "hello")

    assert provider_message_id
    sms = db.query(SMSMessage).first()
    assert sms.to_number == "0700000009"
    assert sms.body == "hello"
