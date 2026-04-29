import httpx
from app.adapters.sms.base import InboundMessage, SMSAdapter, SendResult
from app.config import settings


class AndroidGatewayAdapter(SMSAdapter):
    def send_sms(self, to_number: str, body: str) -> SendResult:
        headers = {"Authorization": f"Bearer {settings.android_gateway_token}"}
        payload = {"to": to_number, "message": body}
        r = httpx.post(settings.android_gateway_url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json() if r.content else {}
        return SendResult(provider_message_id=str(data.get("id")), delivery_status="sent")

    def normalize_inbound(self, payload: dict) -> InboundMessage:
        return InboundMessage(from_number=payload["from"], to_number=payload.get("to", ""), body=payload["message"])
