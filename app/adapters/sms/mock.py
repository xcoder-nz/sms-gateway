from app.adapters.sms.base import InboundMessage, SMSAdapter, SendResult


class MockSMSAdapter(SMSAdapter):
    def send_sms(self, to_number: str, body: str) -> SendResult:
        return SendResult(provider_message_id=None, delivery_status="simulated_delivered")

    def normalize_inbound(self, payload: dict) -> InboundMessage:
        return InboundMessage(
            from_number=payload["from_number"],
            to_number=payload.get("to_number", "DEMO-SHORTCODE"),
            body=payload["body"],
        )
