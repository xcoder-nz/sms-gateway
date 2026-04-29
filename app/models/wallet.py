from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.sql import func
from app.db import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    currency = Column(String, default="AFN", nullable=False)
    balance = Column(Numeric(14, 2), default=0, nullable=False)
    wallet_status = Column(String, default="active", nullable=False)
    version = Column(Integer, default=1, nullable=False)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __mapper_args__ = {"version_id_col": version}
