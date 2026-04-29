import json
import logging
from decimal import Decimal
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.adapters.sms.mock import MockSMSAdapter
from app.db import SessionLocal, get_db
from app.models import MerchantProfile, SMSMessage, Transaction, User, Wallet
from app.services.audit_service import audit_command_decision, audit_state_change, log_event
from app.services.command_parser import parse_command
from app.config import settings
from app.seed.demo_seed import seed_for_session

app = FastAPI(title="SMS Wallet Demo")
app.mount("/static", StaticFiles(directory="app/ui/static"), name="static")
templates = Jinja2Templates(directory="app/ui/templates")
adapter = MockSMSAdapter()
logger = logging.getLogger(__name__)
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_failed_pin_attempts: dict[str, deque[datetime]] = defaultdict(deque)


def enforce_pin_lockout(sender: str):
    now = datetime.now(timezone.utc)
    window = now - timedelta(minutes=5)
    attempts = _failed_pin_attempts[sender]
    while attempts and attempts[0] < window:
        attempts.popleft()
    if len(attempts) >= 5:
        raise HTTPException(429, "Too many PIN attempts")




def require_admin():
    # Demo placeholder until real auth is wired in
    return None



@app.on_event("startup")
def seed_demo_users_on_startup():
    db = SessionLocal()
    try:
        seed_for_session(db)
    except (OperationalError, ProgrammingError):
        logger.warning("Skipping demo seed during startup because database is not initialized yet")
    finally:
        db.close()



@app.get("/health")
def health():
    return {"ok": True, "mode": settings.app_env, "adapter": settings.sms_adapter}


@app.get("/", response_class=HTMLResponse)
def mobile_demo(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).filter(User.role == "buyer").all()
    sms = db.query(SMSMessage).order_by(SMSMessage.id.desc()).limit(25).all()
    return templates.TemplateResponse(request=request, name="mobile_demo.html", context={"request": request, "users": users, "sms": sms})


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request, db: Session = Depends(get_db)):
    total_float = db.query(func.coalesce(func.sum(Wallet.balance), 0)).scalar()
    txns = db.query(Transaction).order_by(Transaction.id.desc()).limit(20).all()
    wallets = db.query(Wallet).all()
    sms = db.query(SMSMessage).order_by(SMSMessage.id.desc()).limit(20).all()
    return templates.TemplateResponse(request=request, name="admin.html", context={"request": request, "total_float": total_float, "txns": txns, "wallets": wallets, "sms": sms})



@app.post("/admin/buyers")
def create_buyer(payload: dict, db: Session = Depends(get_db)):
    full_name = str(payload.get("full_name", "")).strip()
    phone_number = str(payload.get("phone_number", "")).strip()
    pin = str(payload.get("pin", "1234")).strip()
    opening_balance = int(payload.get("opening_balance", 0))

    if not full_name or not phone_number or not pin:
        raise HTTPException(400, "full_name, phone_number and pin are required")

    buyer = User(
        full_name=full_name,
        phone_number=phone_number,
        national_id=f"N-{phone_number}",
        pin_hash=pwd.hash(pin),
        role="buyer",
        status="active",
    )
    db.add(buyer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Buyer phone already exists")

    db.refresh(buyer)
    db.add(Wallet(user_id=buyer.id, currency="AFN", balance=max(opening_balance, 0), wallet_status="active"))
    db.commit()
    return {"ok": True, "buyer_phone": buyer.phone_number}



@app.get("/api/feed/sms")
def feed_sms(db: Session = Depends(get_db)):
    rows = db.query(SMSMessage).order_by(SMSMessage.id.desc()).limit(40).all()
    return [{"id": s.id, "direction": s.direction, "from_number": s.from_number, "to_number": s.to_number, "body": s.body, "created_at": s.created_at.isoformat() if s.created_at else None} for s in rows]


@app.get("/api/feed/transactions")
def feed_transactions(db: Session = Depends(get_db)):
    rows = db.query(Transaction).order_by(Transaction.id.desc()).limit(40).all()
    return [{"id": t.id, "reference": t.reference, "type": t.type, "amount": str(t.amount), "currency": t.currency, "status": t.status, "created_at": t.created_at.isoformat() if t.created_at else None} for t in rows]

@app.post("/api/sms/inbound")
def inbound(payload: dict, request: Request, db: Session = Depends(get_db)):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    correlation_id = getattr(request.state, "correlation_id", str(uuid4()))
    msg = adapter.normalize_inbound(payload)
    db.add(SMSMessage(direction="inbound", from_number=msg.from_number, to_number=msg.to_number, body=msg.body, delivery_status="received"))
    db.commit()
    try:
        cmd = parse_command(msg.body)
    except ValueError:
        audit_command_decision(
            db,
            command="UNKNOWN",
            status="rejected",
            reason_code="INVALID_COMMAND",
            actor=msg.from_number,
            correlation_id=correlation_id,
            request_id=request_id,
            sms_provider_message_id=getattr(msg, "provider_message_id", None),
        )
        raise HTTPException(400, "Invalid command")

    log_event(db, "sms_command", cmd)
    logger.info(json.dumps({"event": "inbound_sms", "correlation_id": correlation_id, "request_id": request_id, "actor": msg.from_number, "command": cmd["cmd"]}))
    return execute_command(msg.from_number, cmd, db, correlation_id=correlation_id, request_id=request_id, sms_ref=getattr(msg, "provider_message_id", None))



@app.post("/api/transactions/pay")
def pay_transaction(payload: dict, db: Session = Depends(get_db)):
    cmd = {
        "cmd": "PAY",
        "merchant_phone": payload["merchant_phone"],
        "amount": int(payload["amount"]),
        "pin": payload["pin"],
    }
    log_event(db, "api_pay_request", {"from_number": payload["from_number"], **cmd})
    return execute_command(payload["from_number"], cmd, db)

@app.get("/api/sms/logs")
def sms_logs(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.query(SMSMessage).order_by(SMSMessage.id.desc()).limit(100).all()


@app.get("/api/network/summary")
def network_summary(db: Session = Depends(get_db)):
    inbound_sms_count = db.query(SMSMessage).filter(SMSMessage.direction == "inbound").count()
    failed_commands = db.query(Transaction).filter(Transaction.status == "rejected").count()
    completed_payments = db.query(Transaction).filter(Transaction.type == "payment", Transaction.status == "completed").count()
    return {
        "inbound_sms_count": inbound_sms_count,
        "failed_commands": failed_commands,
        "completed_payments": completed_payments,
    }


def send_outbound(db: Session, to_number: str, body: str, linked_transaction_id: int | None = None):
    result = adapter.send_sms(to_number, body)
    db.add(SMSMessage(direction="outbound", from_number="DEMO-SWITCH", to_number=to_number, body=body, provider_message_id=result.provider_message_id, delivery_status=result.delivery_status, linked_transaction_id=linked_transaction_id))
    db.commit()


def execute_command(sender: str, cmd: dict, db: Session, correlation_id: str | None = None, request_id: str | None = None, sms_ref: str | None = None):
    user = db.query(User).filter(User.phone_number == sender).first()
    if cmd["cmd"] == "HELP":
        audit_command_decision(db, command="HELP", status="accepted", reason_code="HELP_REQUESTED", actor=sender, correlation_id=correlation_id, request_id=request_id, sms_provider_message_id=sms_ref)
        send_outbound(db, sender, "DEMO HELP: BAL | PAY <merchant_phone> <amount> PIN <pin> | CASHIN <buyer_phone> <amount>")
        return {"ok": True}
    if not user or user.status != "active":
        audit_command_decision(db, command=cmd["cmd"], status="rejected", reason_code="SENDER_NOT_ACTIVE", actor=sender, correlation_id=correlation_id, request_id=request_id, sms_provider_message_id=sms_ref)
        tx = Transaction(reference=str(uuid4())[:12], type=cmd["cmd"].lower(), from_user_id=None, amount=0, currency="AFN", status="rejected", rejection_reason="SENDER_NOT_ACTIVE")
        db.add(tx); db.commit()
        raise HTTPException(404, "Sender not active")
    if cmd["cmd"] == "BAL":
        w = db.query(Wallet).filter(Wallet.user_id == user.id).first()
        send_outbound(db, sender, f"DEMO BALANCE: {w.balance} {w.currency}")
        tx = Transaction(reference=str(uuid4())[:12], type="balance_inquiry", from_user_id=user.id, amount=0, currency="AFN", status="completed")
        db.add(tx); db.commit()
        audit_command_decision(db, command="BAL", status="accepted", reason_code="BALANCE_REQUESTED", actor=sender, amount=0, transaction_reference=tx.reference, correlation_id=correlation_id, request_id=request_id, sms_provider_message_id=sms_ref)
        audit_state_change(db, state_change="BALANCE_INQUIRY_COMPLETED", actor=sender, amount=0, transaction_reference=tx.reference, correlation_id=correlation_id, request_id=request_id)
        return {"ok": True}
    if cmd["cmd"] == "PAY":
        enforce_pin_lockout(sender)
        if not pwd.verify(cmd["pin"], user.pin_hash):
            _failed_pin_attempts[sender].append(datetime.now(timezone.utc))
            audit_command_decision(db, command="PAY", status="rejected", reason_code="INVALID_PIN", actor=sender, target=cmd["merchant_phone"], amount=cmd["amount"], correlation_id=correlation_id, request_id=request_id, sms_provider_message_id=sms_ref)
            raise HTTPException(400, "Invalid PIN")
        _failed_pin_attempts.pop(sender, None)
        merch = db.query(User).filter(User.phone_number == cmd["merchant_phone"], User.role == "merchant", User.status == "active").first()
        if not merch:
            audit_command_decision(db, command="PAY", status="rejected", reason_code="MERCHANT_NOT_FOUND", actor=sender, target=cmd["merchant_phone"], amount=cmd["amount"], correlation_id=correlation_id, request_id=request_id, sms_provider_message_id=sms_ref)
            raise HTTPException(404, "Merchant not found")
        buyer_w = db.query(Wallet).filter(Wallet.user_id == user.id).first()
        merch_w = db.query(Wallet).filter(Wallet.user_id == merch.id).first()
        amount = Decimal(cmd["amount"])
        if amount <= 0:
            audit_command_decision(db, command="PAY", status="rejected", reason_code="INVALID_AMOUNT", actor=sender, target=merch.phone_number, amount=cmd["amount"], correlation_id=correlation_id, request_id=request_id, sms_provider_message_id=sms_ref)
            raise HTTPException(400, "Invalid amount")
        if buyer_w.balance < amount:
            audit_command_decision(db, command="PAY", status="rejected", reason_code="INSUFFICIENT_BALANCE", actor=sender, target=merch.phone_number, amount=cmd["amount"], correlation_id=correlation_id, request_id=request_id, sms_provider_message_id=sms_ref)
            tx = Transaction(reference=str(uuid4())[:12], type="payment", from_user_id=user.id, to_user_id=merch.id, merchant_id=merch.id, amount=amount, currency="AFN", status="rejected", rejection_reason="INSUFFICIENT_BALANCE")
            db.add(tx); db.commit()
            raise HTTPException(400, "Insufficient balance")
        buyer_w.balance -= amount; merch_w.balance += amount
        tx = Transaction(reference=str(uuid4())[:12], type="payment", from_user_id=user.id, to_user_id=merch.id, merchant_id=merch.id, amount=amount, currency="AFN", status="completed")
        db.add(tx); db.commit(); db.refresh(tx)
        send_outbound(db, sender, f"DEMO RECEIPT: Paid {amount} AFN to {merch.full_name}", tx.id)
        send_outbound(db, merch.phone_number, f"DEMO RECEIPT: Received {amount} AFN from {user.full_name}", tx.id)
        audit_command_decision(db, command="PAY", status="accepted", reason_code="PAYMENT_COMPLETED", actor=sender, target=merch.phone_number, amount=amount, transaction_reference=tx.reference, correlation_id=correlation_id, request_id=request_id, sms_provider_message_id=sms_ref)
        audit_state_change(db, state_change="PAYMENT_COMPLETED", actor=sender, target=merch.phone_number, amount=amount, transaction_reference=tx.reference, correlation_id=correlation_id, request_id=request_id)
        logger.info(json.dumps({"event": "payment_completed", "correlation_id": correlation_id, "request_id": request_id, "sms_provider_message_id": sms_ref, "transaction_reference": tx.reference, "amount": str(amount), "actor": sender, "target": merch.phone_number}))
        return {"ok": True, "transaction_reference": tx.reference}
    audit_command_decision(db, command=cmd["cmd"], status="rejected", reason_code="UNSUPPORTED_COMMAND", actor=sender, correlation_id=correlation_id, request_id=request_id, sms_provider_message_id=sms_ref)
    return {"ok": True, "note": "Command accepted"}


@app.exception_handler(HTTPException)
def handle_http_exception(_: Request, exc: HTTPException):
    if exc.status_code >= 500:
        logger.error("http_exception", extra={"status_code": exc.status_code, "detail": exc.detail})
        return JSONResponse(status_code=exc.status_code, content={"ok": False, "message": "Service temporarily unavailable"})
    safe_messages = {
        400: "Invalid request",
        401: "Authentication required",
        403: "Not authorized",
        404: "Resource not found",
        429: "Too many requests",
    }
    message = safe_messages.get(exc.status_code, "Request failed")
    logger.info("request_rejected", extra={"status_code": exc.status_code, "detail": exc.detail})
    return JSONResponse(status_code=exc.status_code, content={"ok": False, "message": message})


@app.exception_handler(RequestValidationError)
def handle_validation_exception(_: Request, exc: RequestValidationError):
    logger.info("validation_failed", extra={"errors": exc.errors()})
    return JSONResponse(status_code=400, content={"ok": False, "message": "Invalid request"})
