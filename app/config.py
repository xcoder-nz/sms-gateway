import os

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "SMS Wallet Demo")
    app_env: str = os.getenv("APP_ENV", "dev")
    debug: bool = os.getenv("DEBUG", "1") == "1"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./sms_wallet_demo.db")
    sms_adapter: str = os.getenv("SMS_ADAPTER", "mock")
    android_gateway_url: str = os.getenv("ANDROID_GATEWAY_URL", "")
    android_gateway_token: str = os.getenv("ANDROID_GATEWAY_TOKEN", "")
    bank_adapter: str = os.getenv("BANK_ADAPTER", "mock")


settings = Settings()
