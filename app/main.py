from decimal import Decimal
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.adapters.sms.mock import MockSMSAdapter
from app.config import settings
from app.db import Base, engine, get_db
from app.models import MerchantProfile, SMSMessage, Transaction, User, Wallet
from app.services.audit_service import log_event
from app.services.command_parser import parse_command

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
app = FastAPI(title="SMS Wallet Demo")
templates = Jinja2Templates(directory="app/ui/templates")
adapter = MockSMSAdapter()
logger = logging.getLogger("sms_gateway")
admin_auth_scheme = HTTPBearer(auto_error=False)
inbound_rate_limit_windows = defaultdict(deque)
pin_attempts = defaultdict(lambda: {"count": 0, "lockout_until": None})
Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"ok": True, "mode": "DEMO/SIMULATED"}

@app.get("/", response_class=HTMLResponse)
def mobile_demo(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).filter(User.role == "buyer").all()
    sms = db.query(SMSMessage).order_by(SMSMessage.id.desc()).limit(25).all()
    return templates.TemplateResponse("mobile_demo.html", {"request": request, "users": users, "sms": sms})

@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    total_float = db.query(func.coalesce(func.sum(Wallet.balance), 0)).scalar()
    txns = db.query(Transaction).order_by(Transaction.id.desc()).limit(20).all()
    wallets = db.query(Wallet).all()
    sms = db.query(SMSMessage).order_by(SMSMessage.id.desc()).limit(20).all()
    return templates.TemplateResponse("admin.html", {"request": request, "total_float": total_float, "txns": txns, "wallets": wallets, "sms": sms})

@app.post("/api/sms/inbound")
def inbound(payload: dict, db: Session = Depends(get_db)):
    from_number = payload.get("from_number", "unknown")
    enforce_inbound_rate_limit(from_number)
    msg = adapter.normalize_inbound(payload)
    db.add(SMSMessage(direction="inbound", from_number=msg.from_number, to_number=msg.to_number, body=msg.body, delivery_status="received"))
    db.commit()
    cmd = parse_command(msg.body)
    log_event(db, "sms_command", cmd)
    return execute_command(msg.from_number, cmd, db)

@app.get("/api/sms/logs")
def sms_logs(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.query(SMSMessage).order_by(SMSMessage.id.desc()).limit(100).all()


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_auth_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not settings.admin_api_token:
        logger.error("admin_auth_not_configured")
        raise HTTPException(503, "Service temporarily unavailable")
    if not credentials or credentials.scheme.lower() != "bearer" or credentials.credentials != settings.admin_api_token:
        logger.info("admin_auth_failed")
        raise HTTPException(401, "Authentication required")
    admin_user = db.query(User).filter(User.role == "admin", User.status == "active").first()
    if not admin_user:
        logger.warning("admin_user_not_found")
        raise HTTPException(403, "Not authorized")
    return admin_user


def enforce_inbound_rate_limit(phone_number: str):
    now = datetime.now(timezone.utc)
    window = inbound_rate_limit_windows[phone_number]
    cutoff = now - timedelta(seconds=settings.inbound_rate_limit_window_seconds)
    while window and window[0] < cutoff:
        window.popleft()
    if len(window) >= settings.inbound_rate_limit_count:
        logger.warning("inbound_rate_limit_exceeded", extra={"phone": phone_number})
        raise HTTPException(429, "Too many requests")
    window.append(now)


def enforce_pin_lockout(phone_number: str):
    attempt_state = pin_attempts[phone_number]
    lockout_until = attempt_state.get("lockout_until")
    if lockout_until and datetime.now(timezone.utc) < lockout_until:
        raise HTTPException(429, "Too many requests")


def record_failed_pin_attempt(phone_number: str):
    attempt_state = pin_attempts[phone_number]
    attempt_state["count"] += 1
    if attempt_state["count"] >= settings.pin_max_attempts:
        attempt_state["lockout_until"] = datetime.now(timezone.utc) + timedelta(seconds=settings.pin_lockout_seconds)
        attempt_state["count"] = 0


def clear_pin_attempts(phone_number: str):
    pin_attempts[phone_number] = {"count": 0, "lockout_until": None}


def send_outbound(db: Session, to_number: str, body: str, linked_transaction_id: int | None = None):
    result = adapter.send_sms(to_number, body)
    db.add(SMSMessage(direction="outbound", from_number="DEMO-SWITCH", to_number=to_number, body=body, provider_message_id=result.provider_message_id, delivery_status=result.delivery_status, linked_transaction_id=linked_transaction_id))
    db.commit()


def execute_command(sender: str, cmd: dict, db: Session):
    user = db.query(User).filter(User.phone_number == sender).first()
    if cmd["cmd"] == "HELP":
        send_outbound(db, sender, "DEMO HELP: BAL | PAY <merchant_phone> <amount> PIN <pin> | CASHIN <buyer_phone> <amount>")
        return {"ok": True}
    if not user or user.status != "active":
        raise HTTPException(404, "Sender not active")
    if cmd["cmd"] == "BAL":
        w = db.query(Wallet).filter(Wallet.user_id == user.id).first()
        send_outbound(db, sender, f"DEMO BALANCE: {w.balance} {w.currency}")
        tx = Transaction(reference=str(uuid4())[:12], type="balance_inquiry", from_user_id=user.id, amount=0, currency="AFN", status="completed")
        db.add(tx); db.commit()
        return {"ok": True}
    if cmd["cmd"] == "PAY":
        enforce_pin_lockout(sender)
        if not pwd.verify(cmd["pin"], user.pin_hash):
            record_failed_pin_attempt(sender)
            raise HTTPException(400, "Invalid request")
        clear_pin_attempts(sender)
        merch = db.query(User).filter(User.phone_number == cmd["merchant_phone"], User.role == "merchant", User.status == "active").first()
        if not merch:
            raise HTTPException(404, "Merchant not found")
        buyer_w = db.query(Wallet).filter(Wallet.user_id == user.id).first()
        merch_w = db.query(Wallet).filter(Wallet.user_id == merch.id).first()
        amount = Decimal(cmd["amount"])
        if amount <= 0 or buyer_w.balance < amount:
            raise HTTPException(400, "Insufficient balance")
        buyer_w.balance -= amount; merch_w.balance += amount
        tx = Transaction(reference=str(uuid4())[:12], type="payment", from_user_id=user.id, to_user_id=merch.id, merchant_id=merch.id, amount=amount, currency="AFN", status="completed")
        db.add(tx); db.commit(); db.refresh(tx)
        send_outbound(db, sender, f"DEMO RECEIPT: Paid {amount} AFN to {merch.full_name}", tx.id)
        send_outbound(db, merch.phone_number, f"DEMO RECEIPT: Received {amount} AFN from {user.full_name}", tx.id)
        return {"ok": True, "transaction_reference": tx.reference}
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
