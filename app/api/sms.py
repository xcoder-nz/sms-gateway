from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.adapters.sms.mock import MockSMSAdapter
from app.api.schemas import SMSOut, SMSResult
from app.db import get_db
from app.models import SMSMessage

router = APIRouter(prefix="/api/sms", tags=["sms"])
adapter = MockSMSAdapter()


@router.post("/send", response_model=SMSResult)
def send_sms(payload: SMSOut, db: Session = Depends(get_db)) -> SMSResult:
    result = adapter.send_sms(payload.to_number, payload.body)
    db.add(
        SMSMessage(
            direction="outbound",
            from_number="DEMO-SWITCH",
            to_number=payload.to_number,
            body=payload.body,
            provider_message_id=result.provider_message_id,
            delivery_status=result.delivery_status,
        )
    )
    db.commit()
    return SMSResult(ok=True, provider_message_id=result.provider_message_id, delivery_status=result.delivery_status)
