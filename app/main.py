import json
import logging
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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.adapters.sms.mock import MockSMSAdapter
from app.config import settings
from app.db import Base, engine, get_db
from app.models import MerchantProfile, SMSMessage, Transaction, User, Wallet
from app.services.audit_service import audit_command_decision, audit_state_change, log_event
from app.services.command_parser import parse_command

app = FastAPI(title="SMS Wallet Demo")
templates = Jinja2Templates(directory="app/ui/templates")
adapter = MockSMSAdapter()
logger = logging.getLogger("sms_gateway")
admin_auth_scheme = HTTPBearer(auto_error=False)
inbound_rate_limit_windows = defaultdict(deque)
pin_attempts = defaultdict(lambda: {"count": 0, "lockout_until": None})
Base.metadata.create_all(bind=engine)
logger = logging.getLogger("sms_gateway")


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    correlation_id = request.headers.get("x-correlation-id") or str(uuid4())
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["x-correlation-id"] = correlation_id
    return response

app.include_router(health_router)
app.include_router(sms_router)
app.include_router(users_router)
app.include_router(wallets_router)
app.include_router(transactions_router)
app.include_router(merchants_router)
app.include_router(network_router)

def _digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


@app.exception_handler(RequestValidationError)
def request_validation_handler(_: Request, exc: RequestValidationError):
    details = [ErrorDetail(field=".".join(str(p) for p in e["loc"][1:]), message=e["msg"]).model_dump() for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={"ok": False, "error_code": "validation_failed", "message": "Request payload validation failed", "details": details},
    )


@app.exception_handler(HTTPException)
def http_exception_handler(_: Request, exc: HTTPException):
    code = "business_rule_rejected" if exc.status_code in (400, 404, 409) else "http_error"
    return JSONResponse(
        status_code=exc.status_code,
        content={"ok": False, "error_code": code, "message": str(exc.detail), "details": []},
    )


def _to_decimal(amount: str | int | float | Decimal) -> Decimal:
    try:
        value = Decimal(str(amount)).quantize(Decimal("0.01"))
    except Exception as exc:
        raise HTTPException(400, "Invalid amount") from exc
    if value <= Decimal("0.00"):
        raise HTTPException(400, "Amount must be positive")
    return value


def _process_payment(
    db: Session,
    buyer: User,
    merchant: User,
    amount: Decimal,
    idempotency_key: str | None = None,
):
    if idempotency_key:
        existing = db.query(Transaction).filter(Transaction.idempotency_key == idempotency_key).first()
        if existing:
            return existing

    with db.begin():
        wallet_ids = sorted([buyer.id, merchant.id])
        wallets = (
            db.query(Wallet)
            .filter(Wallet.user_id.in_(wallet_ids))
            .with_for_update()
            .all()
        )
        wallet_by_user = {w.user_id: w for w in wallets}
        buyer_w = wallet_by_user.get(buyer.id)
        merch_w = wallet_by_user.get(merchant.id)
        if not buyer_w or not merch_w:
            raise HTTPException(404, "Wallet not found")
        if buyer_w.balance < amount:
            raise HTTPException(400, "Insufficient balance")

        buyer_w.balance -= amount
        merch_w.balance += amount
        tx = Transaction(
            reference=str(uuid4())[:12],
            type="payment",
            from_user_id=buyer.id,
            to_user_id=merchant.id,
            merchant_id=merchant.id,
            amount=amount,
            currency="AFN",
            status="completed",
            idempotency_key=idempotency_key,
        )
        db.add(tx)

    db.refresh(tx)
    return tx



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
def inbound(payload: dict, request: Request, db: Session = Depends(get_db)):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    correlation_id = request.state.correlation_id
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
            sms_provider_message_id=msg.provider_message_id,
        )
        raise HTTPException(400, "Invalid command")

    log_event(db, "sms_command", cmd)
    logger.info(json.dumps({"event": "inbound_sms", "correlation_id": correlation_id, "request_id": request_id, "actor": msg.from_number, "command": cmd["cmd"]}))
    return execute_command(msg.from_number, cmd, db, correlation_id=correlation_id, request_id=request_id, sms_ref=msg.provider_message_id)


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
            audit_command_decision(db, command="PAY", status="rejected", reason_code="INVALID_PIN", actor=sender, target=cmd["merchant_phone"], amount=cmd["amount"], correlation_id=correlation_id, request_id=request_id, sms_provider_message_id=sms_ref)
            raise HTTPException(400, "Invalid PIN")
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
