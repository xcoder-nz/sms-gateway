from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from app.db import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
