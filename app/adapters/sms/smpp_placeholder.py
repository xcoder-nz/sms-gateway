from app.adapters.sms.base import InboundMessage, SMSAdapter, SendResult


class SMPPAdapter(SMSAdapter):
    """TODO: implement SMPP/local aggregator integration."""
    def send_sms(self, to_number: str, body: str) -> SendResult:
        raise NotImplementedError("TODO: SMPP adapter")

    def normalize_inbound(self, payload: dict) -> InboundMessage:
        raise NotImplementedError("TODO: SMPP adapter")
