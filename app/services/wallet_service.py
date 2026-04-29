from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import User, Wallet


@dataclass
class BalanceResult:
    user_id: int
    balance: Decimal
    currency: str


class WalletService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_balance(self, user: User) -> BalanceResult:
        wallet = self.db.query(Wallet).filter(Wallet.user_id == user.id).first()
        if wallet is None:
            raise ValueError("Wallet not found")
        return BalanceResult(user_id=user.id, balance=wallet.balance, currency=wallet.currency)
