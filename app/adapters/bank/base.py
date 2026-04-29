class BankAdapter:
    def create_wallet_account(self, user_id: int):
        raise NotImplementedError

    def get_balance(self, account_ref: str):
        raise NotImplementedError

    def post_settlement_event(self, payload: dict):
        raise NotImplementedError

    def validate_customer_identity(self, national_id: str):
        raise NotImplementedError
