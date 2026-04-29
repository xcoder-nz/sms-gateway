from app.adapters.bank.base import BankAdapter


class FlexcubeAdapterPlaceholder(BankAdapter):
    """Placeholder for future FLEXCUBE integration.
    Assumes both REST and SOAP/XML gateway integration modes may be required.
    """
    def create_wallet_account(self, user_id: int):
        raise NotImplementedError("TODO: FLEXCUBE REST/SOAP integration")

    def get_balance(self, account_ref: str):
        raise NotImplementedError("TODO: FLEXCUBE REST/SOAP integration")

    def post_settlement_event(self, payload: dict):
        raise NotImplementedError("TODO: FLEXCUBE REST/SOAP integration")

    def validate_customer_identity(self, national_id: str):
        raise NotImplementedError("TODO: FLEXCUBE REST/SOAP integration")
