from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "SMS Wallet Demo")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./sms_wallet_demo.db")
    sms_adapter: str = os.getenv("SMS_ADAPTER", "mock")
    android_gateway_url: str = os.getenv("ANDROID_GATEWAY_URL", "")
    android_gateway_token: str = os.getenv("ANDROID_GATEWAY_TOKEN", "")
    bank_adapter: str = os.getenv("BANK_ADAPTER", "mock")
    admin_api_token: str = os.getenv("ADMIN_API_TOKEN", "")
    inbound_rate_limit_count: int = int(os.getenv("INBOUND_RATE_LIMIT_COUNT", "10"))
    inbound_rate_limit_window_seconds: int = int(os.getenv("INBOUND_RATE_LIMIT_WINDOW_SECONDS", "60"))
    pin_max_attempts: int = int(os.getenv("PIN_MAX_ATTEMPTS", "5"))
    pin_lockout_seconds: int = int(os.getenv("PIN_LOCKOUT_SECONDS", "300"))


settings = Settings()
