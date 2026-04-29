from dataclasses import dataclass


@dataclass
class SendResult:
    provider_message_id: str | None
    delivery_status: str


@dataclass
class InboundMessage:
    from_number: str
    to_number: str
    body: str


class SMSAdapter:
    def send_sms(self, to_number: str, body: str) -> SendResult:
        raise NotImplementedError

    def normalize_inbound(self, payload: dict) -> InboundMessage:
        raise NotImplementedError

    def healthcheck(self) -> dict:
        return {"ok": True}
