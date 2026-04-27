"""ISEYAA Events Service — Configuration"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me"

    DATABASE_URL: str = "postgresql+asyncpg://iseyaa_user:password@localhost:5442/iseyaa_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 5
    DATABASE_POOL_TIMEOUT: int = 30

    MONGODB_URL: str = "mongodb://iseyaa_mongo:password@localhost:27017/iseyaa_content"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"

    AWS_REGION: str = "af-south-1"
    AWS_S3_BUCKET: str = "iseyaa-media-dev"

    PAYSTACK_SECRET_KEY: str = "sk_test_changeme"
    PAYSTACK_CALLBACK_URL: str = "http://localhost:8000/api/v1/payments/paystack/callback"

    ABLY_API_KEY: Optional[str] = None   # Live event streaming


@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
