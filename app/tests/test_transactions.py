from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.main import execute_command
from app.models import Transaction, User, Wallet


def _buyer_cmd(amount: int = 50, pin: str = "1234", merchant_phone: str = "0799001100"):
    return {"cmd": "PAY", "merchant_phone": merchant_phone, "amount": amount, "pin": pin}


def test_wallet_balance_checks_and_pin_outcomes(db_session):
    with pytest.raises(HTTPException, match="Invalid PIN"):
        execute_command("0700123456", _buyer_cmd(pin="0000"), db_session)

    with pytest.raises(HTTPException, match="Insufficient balance"):
        execute_command("0700123456", _buyer_cmd(amount=5000), db_session)


def test_merchant_validation_and_rejection_reason(db_session):
    with pytest.raises(HTTPException, match="Merchant not found"):
        execute_command("0700123456", _buyer_cmd(merchant_phone="0700999999"), db_session)

    buyer = db_session.query(User).filter(User.phone_number == "0700123456").first()
    merchant = db_session.query(User).filter(User.phone_number == "0799001100").first()
    buyer_w = db_session.query(Wallet).filter(Wallet.user_id == buyer.id).first()
    merchant_w = db_session.query(Wallet).filter(Wallet.user_id == merchant.id).first()

    before_buyer = Decimal(buyer_w.balance)
    before_merchant = Decimal(merchant_w.balance)
    result = execute_command("0700123456", _buyer_cmd(amount=100), db_session)

    assert result["ok"] is True
    db_session.refresh(buyer_w)
    db_session.refresh(merchant_w)
    assert Decimal(buyer_w.balance) == before_buyer - Decimal("100")
    assert Decimal(merchant_w.balance) == before_merchant + Decimal("100")

    tx = db_session.query(Transaction).filter(Transaction.reference == result["transaction_reference"]).first()
    assert tx.status == "completed"
    assert tx.rejection_reason is None
