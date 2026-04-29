from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Transaction, User, Wallet



@dataclass
class ServiceResult:
    status: str
    transaction_id: int | None = None
    reference: str | None = None
    reason: str | None = None
    amount: Decimal | None = None


class TransactionService:
    def __init__(self, db: Session):
        self.db = db

    def _reject(self, tx_type: str, from_user_id: int | None, amount: Decimal, reason: str) -> ServiceResult:
        tx = Transaction(
            reference=str(uuid4())[:12],
            type=tx_type,
            from_user_id=from_user_id,
            amount=amount,
            currency="AFN",
            status="rejected",
            rejection_reason=reason,
        )
        self.db.add(tx)
        self.db.commit()
        self.db.refresh(tx)
        return ServiceResult(status="rejected", transaction_id=tx.id, reference=tx.reference, reason=reason, amount=amount)

    def create_balance_inquiry(self, user: User) -> ServiceResult:
        tx = Transaction(reference=str(uuid4())[:12], type="balance_inquiry", from_user_id=user.id, amount=0, currency="AFN", status="completed")
        self.db.add(tx)
        self.db.commit()
        self.db.refresh(tx)
        return ServiceResult(status="completed", transaction_id=tx.id, reference=tx.reference, amount=Decimal("0"))

    def pay(self, buyer: User, merchant_phone: str, amount: Decimal, pin: str) -> ServiceResult:
        if pin != buyer.pin_hash:
            return self._reject("payment", buyer.id, amount, "invalid_pin")
        merchant = self.db.query(User).filter(User.phone_number == merchant_phone, User.role == "merchant", User.status == "active").first()
        if merchant is None:
            return self._reject("payment", buyer.id, amount, "merchant_not_found")
        buyer_wallet = self.db.query(Wallet).filter(Wallet.user_id == buyer.id).first()
        merchant_wallet = self.db.query(Wallet).filter(Wallet.user_id == merchant.id).first()
        if buyer_wallet is None or merchant_wallet is None:
            return self._reject("payment", buyer.id, amount, "wallet_not_found")
        if amount <= 0:
            return self._reject("payment", buyer.id, amount, "invalid_amount")
        if buyer_wallet.balance < amount:
            return self._reject("payment", buyer.id, amount, "insufficient_balance")

        buyer_wallet.balance -= amount
        merchant_wallet.balance += amount
        tx = Transaction(
            reference=str(uuid4())[:12],
            type="payment",
            from_user_id=buyer.id,
            to_user_id=merchant.id,
            merchant_id=merchant.id,
            amount=amount,
            currency="AFN",
            status="completed",
        )
        self.db.add(tx)
        self.db.commit()
        self.db.refresh(tx)
        return ServiceResult(status="completed", transaction_id=tx.id, reference=tx.reference, amount=amount)

    def cashin(self, actor: User, buyer_phone: str, amount: Decimal) -> ServiceResult:
        return self._reject("cashin", actor.id, amount, "not_implemented")

    def cashout(self, actor: User, buyer_phone: str, amount: Decimal) -> ServiceResult:
        return self._reject("cashout", actor.id, amount, "not_implemented")
