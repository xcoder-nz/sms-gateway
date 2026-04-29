from app.seed.demo_seed import seed
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import TransactionOut
from app.db import get_db
from app.models import Transaction

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionOut])
def list_transactions(db: Session = Depends(get_db)) -> list[Transaction]:
    return db.query(Transaction).order_by(Transaction.id.desc()).all()


@router.post("/pay", response_model=TransactionOut)
def pay_transaction(db: Session = Depends(get_db)) -> Transaction:
    tx = Transaction(reference="MANUAL-PAY", type="payment", amount=0, currency="AFN", status="queued")
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.post("/reset-demo")
def reset_demo(db: Session = Depends(get_db)) -> dict:
    seed(db)
    return {"ok": True}
