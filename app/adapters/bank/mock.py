from app.adapters.bank.base import BankAdapter


class MockBankAdapter(BankAdapter):
    def create_wallet_account(self, user_id: int):
        return {"simulated": True, "account_ref": f"DEMO-{user_id}"}

    def get_balance(self, account_ref: str):
        return {"simulated": True, "balance": 0}

    def post_settlement_event(self, payload: dict):
        return {"simulated": True, "accepted": True}

    def validate_customer_identity(self, national_id: str):
        return {"simulated": True, "valid": True}
