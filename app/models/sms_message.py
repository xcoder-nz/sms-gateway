from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from app.db import Base


class SMSMessage(Base):
    __tablename__ = "sms_messages"

    id = Column(Integer, primary_key=True)
    direction = Column(String, nullable=False)
    from_number = Column(String, nullable=False)
    to_number = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    provider_message_id = Column(String, nullable=True)
    delivery_status = Column(String, default="queued", nullable=False)
    linked_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
