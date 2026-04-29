from decimal import Decimal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.adapters.sms.mock import MockSMSAdapter
from app.db import Base, engine, get_db
from app.models import MerchantProfile, SMSMessage, Transaction, User, Wallet
from app.schemas.api_responses import ErrorDetail
from app.schemas.sms import InboundSMSRequest
from app.services.audit_service import log_event
from app.services.command_parser import parse_command

app = FastAPI(title="SMS Wallet Demo")
templates = Jinja2Templates(directory="app/ui/templates")
Base.metadata.create_all(bind=engine)

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


@app.get("/health")
def health():
    return {"ok": True, "mode": "DEMO/SIMULATED"}

@app.get("/", response_class=HTMLResponse)
def mobile_demo(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).filter(User.role == "buyer").all()
    sms = db.query(SMSMessage).order_by(SMSMessage.id.desc()).limit(25).all()
    return templates.TemplateResponse("mobile_demo.html", {"request": request, "users": users, "sms": sms})

@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request, db: Session = Depends(get_db)):
    total_float = db.query(func.coalesce(func.sum(Wallet.balance), 0)).scalar()
    txns = db.query(Transaction).order_by(Transaction.id.desc()).limit(20).all()
    wallets = db.query(Wallet).all()
    sms = db.query(SMSMessage).order_by(SMSMessage.id.desc()).limit(20).all()
    return templates.TemplateResponse("admin.html", {"request": request, "total_float": total_float, "txns": txns, "wallets": wallets, "sms": sms})

@app.post("/api/sms/inbound")
def inbound(payload: InboundSMSRequest, db: Session = Depends(get_db)):
    msg = adapter.normalize_inbound(payload.model_dump())
    db.add(SMSMessage(direction="inbound", from_number=msg.from_number, to_number=msg.to_number, body=msg.body, delivery_status="received"))
    db.commit()
    cmd = parse_command(msg.body)
    log_event(db, "sms_command", cmd)
    return execute_command(msg.from_number, cmd, db)



def send_outbound(db: Session, to_number: str, body: str, linked_transaction_id: int | None = None):
    result = adapter.send_sms(to_number, body)
    db.add(SMSMessage(direction="outbound", from_number="DEMO-SWITCH", to_number=to_number, body=body, provider_message_id=result.provider_message_id, delivery_status=result.delivery_status, linked_transaction_id=linked_transaction_id))
    db.commit()


def execute_command(sender: str, cmd: dict, db: Session):
    sender_digits = _digits_only(sender)
    user = next((candidate for candidate in db.query(User).all() if _digits_only(candidate.phone_number) == sender_digits), None)
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
        if not pwd.verify(cmd["pin"], user.pin_hash):
            raise HTTPException(400, "Invalid PIN")
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
