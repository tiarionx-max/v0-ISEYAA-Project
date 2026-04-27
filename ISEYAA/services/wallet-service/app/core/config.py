"""ISEYAA Wallet Service — Configuration"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me"

    # Isolated wallet DB (separate RDS instance)
    DATABASE_URL: str = "postgresql+asyncpg://iseyaa_wallet:password@localhost:5443/iseyaa_wallet_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30

    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"

    AWS_REGION: str = "af-south-1"

    # Paystack
    PAYSTACK_SECRET_KEY: str = "sk_test_changeme"
    PAYSTACK_PUBLIC_KEY: str = "pk_test_changeme"
    PAYSTACK_WEBHOOK_SECRET: str = "changeme"
    PAYSTACK_CALLBACK_URL: str = "http://localhost:8000/api/v1/payments/paystack/callback"

    # Flutterwave
    FLUTTERWAVE_SECRET_KEY: str = "FLWSECK_TEST-changeme"
    FLUTTERWAVE_WEBHOOK_HASH: str = "changeme"

    # OGIRS (Ogun State Revenue)
    OGIRS_API_KEY: Optional[str] = None
    OGIRS_BASE_URL: str = "https://api.ogirs.gov.ng/v1"


@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
