from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import NetworkFlow, NetworkSummary
from app.db import get_db
from app.models import MerchantProfile, Transaction, User, Wallet

router = APIRouter(prefix="/api/network", tags=["network"])


@router.get("/summary", response_model=NetworkSummary)
def network_summary(db: Session = Depends(get_db)) -> NetworkSummary:
    return NetworkSummary(
        users=db.query(User).count(),
        merchants=db.query(MerchantProfile).count(),
        wallets=db.query(Wallet).count(),
        transactions=db.query(Transaction).count(),
    )


@router.get("/recent-flow", response_model=list[NetworkFlow])
def recent_flow(db: Session = Depends(get_db)) -> list[NetworkFlow]:
    txs = db.query(Transaction).order_by(Transaction.id.desc()).limit(20).all()
    return [NetworkFlow(reference=t.reference, amount=t.amount, from_user_id=t.from_user_id, to_user_id=t.to_user_id, status=t.status) for t in txs]
