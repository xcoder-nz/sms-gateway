from decimal import Decimal

from app.models import AuditEvent, SMSMessage, User, Wallet


def test_inbound_sms_bal_and_audit_log(client, db_session):
    resp = client.post("/api/sms/inbound", json={"from_number": "0700123456", "body": "BAL"})
    assert resp.status_code == 200

    logs = db_session.query(SMSMessage).all()
    assert len(logs) == 2
    assert any(m.direction == "inbound" and m.body == "BAL" for m in logs)
    assert any(m.direction == "outbound" and "DEMO BALANCE" in m.body for m in logs)

    events = db_session.query(AuditEvent).all()
    assert any(e.event_type == "sms_command" for e in events)


def test_transactions_pay_wallet_deltas_sms_logs_and_audit_events(client, db_session):
    buyer = db_session.query(User).filter(User.phone_number == "0700123456").first()
    merchant = db_session.query(User).filter(User.phone_number == "0799001100").first()
    buyer_w = db_session.query(Wallet).filter(Wallet.user_id == buyer.id).first()
    merchant_w = db_session.query(Wallet).filter(Wallet.user_id == merchant.id).first()
    before_buyer = Decimal(buyer_w.balance)
    before_merchant = Decimal(merchant_w.balance)

    resp = client.post(
        "/api/transactions/pay",
        json={"from_number": "0700123456", "merchant_phone": "0799001100", "amount": 130, "pin": "1234"},
    )
    assert resp.status_code == 200

    db_session.refresh(buyer_w)
    db_session.refresh(merchant_w)
    assert Decimal(buyer_w.balance) == before_buyer - Decimal("130")
    assert Decimal(merchant_w.balance) == before_merchant + Decimal("130")

    outbound = db_session.query(SMSMessage).filter(SMSMessage.direction == "outbound").all()
    assert len(outbound) == 2
    assert any("Paid 130" in m.body for m in outbound)
    assert any("Received 130" in m.body for m in outbound)

    events = db_session.query(AuditEvent).all()
    assert any(e.event_type == "api_pay_request" for e in events)
