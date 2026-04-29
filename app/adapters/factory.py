from __future__ import annotations

from app.adapters.bank.base import BankAdapter
from app.adapters.bank.flexcube_placeholder import FlexcubeAdapterPlaceholder
from app.adapters.bank.mock import MockBankAdapter
from app.adapters.sms.android_gateway import AndroidGatewayAdapter
from app.adapters.sms.base import SMSAdapter
from app.adapters.sms.mock import MockSMSAdapter
from app.adapters.sms.smpp_placeholder import SMPPAdapter
from app.config import settings


class AdapterConfigError(ValueError):
    pass


def get_sms_adapter() -> SMSAdapter:
    sms_adapter = settings.sms_adapter.lower().strip()
    if sms_adapter == "mock":
        return MockSMSAdapter()
    if sms_adapter == "android_gateway":
        return AndroidGatewayAdapter()
    if sms_adapter == "smpp_placeholder":
        return SMPPAdapter()
    raise AdapterConfigError(
        f"Invalid SMS_ADAPTER '{settings.sms_adapter}'. Supported values: mock, android_gateway, smpp_placeholder."
    )


def get_bank_adapter() -> BankAdapter:
    bank_adapter = settings.bank_adapter.lower().strip()
    if bank_adapter == "mock":
        return MockBankAdapter()
    if bank_adapter == "flexcube_placeholder":
        return FlexcubeAdapterPlaceholder()
    raise AdapterConfigError(
        f"Invalid BANK_ADAPTER '{settings.bank_adapter}'. Supported values: mock, flexcube_placeholder."
    )


def validate_adapter_configuration() -> None:
    get_sms_adapter()
    get_bank_adapter()
