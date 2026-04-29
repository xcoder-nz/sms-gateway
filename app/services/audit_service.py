import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


COMMAND_AUDIT_MATRIX = {
    "HELP": {"accepted": ["HELP_REQUESTED"], "rejected": []},
    "BAL": {"accepted": ["BALANCE_REQUESTED"], "rejected": ["SENDER_NOT_ACTIVE"]},
    "PAY": {
        "accepted": ["PAYMENT_COMPLETED"],
        "rejected": [
            "SENDER_NOT_ACTIVE",
            "INVALID_PIN",
            "MERCHANT_NOT_FOUND",
            "INVALID_AMOUNT",
            "INSUFFICIENT_BALANCE",
        ],
    },
    "CASHIN": {"accepted": [], "rejected": ["UNSUPPORTED_COMMAND"]},
    "CASHOUT": {"accepted": [], "rejected": ["UNSUPPORTED_COMMAND"]},
    "UNKNOWN": {"accepted": [], "rejected": ["INVALID_COMMAND"]},
}


def log_event(db: Session, event_type: str, payload: dict[str, Any]):
    db.add(AuditEvent(event_type=event_type, payload_json=json.dumps(payload)))
    db.commit()


def audit_command_decision(
    db: Session,
    *,
    command: str,
    status: str,
    reason_code: str,
    actor: str,
    target: str | None = None,
    amount: str | int | float | None = None,
    transaction_reference: str | None = None,
    correlation_id: str | None = None,
    request_id: str | None = None,
    sms_provider_message_id: str | None = None,
):
    payload = {
        "command": command,
        "status": status,
        "reason_code": reason_code,
        "actor": actor,
        "target": target,
        "amount": str(amount) if amount is not None else None,
        "transaction_reference": transaction_reference,
        "correlation_id": correlation_id,
        "request_id": request_id,
        "sms_provider_message_id": sms_provider_message_id,
    }
    log_event(db, "command_decision", payload)


def audit_state_change(
    db: Session,
    *,
    state_change: str,
    actor: str,
    target: str | None = None,
    amount: str | int | float | None = None,
    transaction_reference: str | None = None,
    correlation_id: str | None = None,
    request_id: str | None = None,
):
    payload = {
        "state_change": state_change,
        "actor": actor,
        "target": target,
        "amount": str(amount) if amount is not None else None,
        "transaction_reference": transaction_reference,
        "correlation_id": correlation_id,
        "request_id": request_id,
    }
    log_event(db, "state_change", payload)
