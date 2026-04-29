from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import WalletAction, WalletOut
from app.db import get_db
from app.models import Transaction, Wallet

router = APIRouter(prefix="/api/wallets", tags=["wallets"])


def _wallet_or_404(wallet_id: int, db: Session) -> Wallet:
    wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
    if not wallet:
        raise HTTPException(404, "Wallet not found")
    return wallet


@router.get("", response_model=list[WalletOut])
def list_wallets(db: Session = Depends(get_db)) -> list[Wallet]:
    return db.query(Wallet).order_by(Wallet.id.asc()).all()


@router.get("/{wallet_id}", response_model=WalletOut)
def get_wallet(wallet_id: int, db: Session = Depends(get_db)) -> Wallet:
    return _wallet_or_404(wallet_id, db)


@router.post("/{wallet_id}/cashin", response_model=WalletOut)
def wallet_cashin(wallet_id: int, payload: WalletAction, db: Session = Depends(get_db)) -> Wallet:
    wallet = _wallet_or_404(wallet_id, db)
    if payload.amount <= Decimal("0"):
        raise HTTPException(400, "Amount must be positive")
    wallet.balance += payload.amount
    db.add(Transaction(reference=f"CIN-{wallet.id}-{abs(hash(str(payload.amount)))%100000}", type="cashin", to_user_id=wallet.user_id, amount=payload.amount, currency=wallet.currency, status="completed"))
    db.commit(); db.refresh(wallet)
    return wallet


@router.post("/{wallet_id}/cashout", response_model=WalletOut)
def wallet_cashout(wallet_id: int, payload: WalletAction, db: Session = Depends(get_db)) -> Wallet:
    wallet = _wallet_or_404(wallet_id, db)
    if payload.amount <= Decimal("0"):
        raise HTTPException(400, "Amount must be positive")
    if wallet.balance < payload.amount:
        raise HTTPException(400, "Insufficient balance")
    wallet.balance -= payload.amount
    db.add(Transaction(reference=f"COUT-{wallet.id}-{abs(hash(str(payload.amount)))%100000}", type="cashout", from_user_id=wallet.user_id, amount=payload.amount, currency=wallet.currency, status="completed"))
    db.commit(); db.refresh(wallet)
    return wallet
