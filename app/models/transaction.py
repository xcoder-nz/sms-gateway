from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.sql import func
from app.db import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    reference = Column(String, unique=True, nullable=False)
    type = Column(String, nullable=False)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    merchant_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String, default="AFN", nullable=False)
    status = Column(String, nullable=False)
    rejection_reason = Column(String, nullable=True)
    idempotency_key = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
