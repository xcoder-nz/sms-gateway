import pytest

from app.adapters.sms.android_gateway import AndroidGatewayAdapter
from app.adapters.sms.base import InboundMessage, SendResult
from app.adapters.sms.mock import MockSMSAdapter


@pytest.mark.parametrize("adapter_cls,payload", [(MockSMSAdapter, {"from_number": "1", "to_number": "2", "body": "BAL"}), (AndroidGatewayAdapter, {"from": "1", "to": "2", "message": "BAL"})])
def test_adapter_contract_normalize_and_healthcheck(adapter_cls, payload):
    adapter = adapter_cls()
    msg = adapter.normalize_inbound(payload)
    assert isinstance(msg, InboundMessage)
    assert msg.from_number == "1"
    assert msg.to_number == "2"
    assert msg.body == "BAL"

    health = adapter.healthcheck()
    assert isinstance(health, dict)
    assert health.get("ok") is True


def test_mock_send_sms_contract():
    result = MockSMSAdapter().send_sms("0700", "hello")
    assert isinstance(result, SendResult)
    assert result.delivery_status
