from sqlalchemy.orm import Session

from app.adapters.sms.mock import MockSMSAdapter
from app.models import SMSMessage


class NotificationService:
    def __init__(self, db: Session, adapter: MockSMSAdapter):
        self.db = db
        self.adapter = adapter

    def send_sms(self, to_number: str, body: str, linked_transaction_id: int | None = None) -> str:
        result = self.adapter.send_sms(to_number, body)
        self.db.add(
            SMSMessage(
                direction="outbound",
                from_number="DEMO-SWITCH",
                to_number=to_number,
                body=body,
                provider_message_id=result.provider_message_id,
                delivery_status=result.delivery_status,
                linked_transaction_id=linked_transaction_id,
            )
        )
        self.db.commit()
        return result.provider_message_id
