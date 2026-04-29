import json
from sqlalchemy.orm import Session
from app.models.audit_event import AuditEvent


def log_event(db: Session, event_type: str, payload: dict):
    db.add(AuditEvent(event_type=event_type, payload_json=json.dumps(payload)))
    db.commit()
