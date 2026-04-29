from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.adapters.sms.mock import MockSMSAdapter
from app.db import Base, engine, get_db
from app.models import SMSMessage, Transaction, User, Wallet
from app.services.audit_service import log_event
from app.services.command_parser import parse_command
from app.services.notification_service import NotificationService
from app.services.transaction_service import TransactionService
from app.services.wallet_service import WalletService

app = FastAPI(title="SMS Wallet Demo")
templates = Jinja2Templates(directory="app/ui/templates")
adapter = MockSMSAdapter()
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
def admin(request: Request, db: Session = Depends(get_db)):
    total_float = db.query(func.coalesce(func.sum(Wallet.balance), 0)).scalar()
    txns = db.query(Transaction).order_by(Transaction.id.desc()).limit(20).all()
    wallets = db.query(Wallet).all()
    sms = db.query(SMSMessage).order_by(SMSMessage.id.desc()).limit(20).all()
    return templates.TemplateResponse("admin.html", {"request": request, "total_float": total_float, "txns": txns, "wallets": wallets, "sms": sms})

@app.post("/api/sms/inbound")
def inbound(payload: dict, db: Session = Depends(get_db)):
    msg = adapter.normalize_inbound(payload)
    db.add(SMSMessage(direction="inbound", from_number=msg.from_number, to_number=msg.to_number, body=msg.body, delivery_status="received"))
    db.commit()
    cmd = parse_command(msg.body)
    log_event(db, "sms_command", cmd)
    return execute_command(msg.from_number, cmd, db)

@app.get("/api/sms/logs")
def sms_logs(db: Session = Depends(get_db)):
    return db.query(SMSMessage).order_by(SMSMessage.id.desc()).limit(100).all()



def execute_command(sender: str, cmd: dict, db: Session):
    user = db.query(User).filter(User.phone_number == sender).first()
    notifier = NotificationService(db, adapter)
    wallet_service = WalletService(db)
    tx_service = TransactionService(db)

    if cmd["cmd"] == "HELP":
        notifier.send_sms(sender, "DEMO HELP: BAL | PAY <merchant_phone> <amount> PIN <pin> | CASHIN <buyer_phone> <amount>")
        return {"ok": True}

    if not user or user.status != "active":
        raise HTTPException(404, "Sender not active")

    if cmd["cmd"] == "BAL":
        balance_result = wallet_service.get_user_balance(user)
        notifier.send_sms(sender, f"DEMO BALANCE: {balance_result.balance} {balance_result.currency}")
        tx_service.create_balance_inquiry(user)
        return {"ok": True}

    if cmd["cmd"] == "PAY":
        pay_result = tx_service.pay(
            buyer=user,
            merchant_phone=cmd["merchant_phone"],
            amount=Decimal(cmd["amount"]),
            pin=cmd["pin"],
        )
        if pay_result.status == "rejected":
            error_map = {
                "invalid_pin": (400, "Invalid PIN"),
                "merchant_not_found": (404, "Merchant not found"),
                "wallet_not_found": (404, "Wallet not found"),
                "invalid_amount": (400, "Invalid amount"),
                "insufficient_balance": (400, "Insufficient balance"),
            }
            status_code, detail = error_map.get(pay_result.reason, (400, "Payment rejected"))
            raise HTTPException(status_code, detail)

        merchant = db.query(User).filter(User.phone_number == cmd["merchant_phone"]).first()
        notifier.send_sms(sender, f"DEMO RECEIPT: Paid {pay_result.amount} AFN to {merchant.full_name}", pay_result.transaction_id)
        notifier.send_sms(merchant.phone_number, f"DEMO RECEIPT: Received {pay_result.amount} AFN from {user.full_name}", pay_result.transaction_id)
        return {"ok": True, "transaction_reference": pay_result.reference}

    if cmd["cmd"] == "CASHIN":
        result = tx_service.cashin(user, cmd["buyer_phone"], Decimal(cmd["amount"]))
        return {"ok": True, "status": result.status, "reason": result.reason, "transaction_reference": result.reference}

    if cmd["cmd"] == "CASHOUT":
        result = tx_service.cashout(user, cmd["buyer_phone"], Decimal(cmd["amount"]))
        return {"ok": True, "status": result.status, "reason": result.reason, "transaction_reference": result.reference}

    return {"ok": True, "note": "Command accepted"}
