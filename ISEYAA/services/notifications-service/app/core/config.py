"""ISEYAA Notifications Service — Configuration"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://iseyaa_user:password@localhost:5442/iseyaa_db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 3
    DATABASE_POOL_TIMEOUT: int = 30

    REDIS_URL: str = "redis://localhost:6379/0"
    AWS_REGION: str = "af-south-1"
    AWS_SQS_NOTIFICATIONS_QUEUE_URL: Optional[str] = None

    # Termii (SMS — Nigerian-first)
    TERMII_API_KEY: Optional[str] = None
    TERMII_SENDER_ID: str = "ISEYAA"
    TERMII_BASE_URL: str = "https://api.ng.termii.com/api"

    # SendGrid
    SENDGRID_API_KEY: Optional[str] = None
    SENDGRID_FROM_EMAIL: str = "noreply@iseyaa.og.gov.ng"
    SENDGRID_FROM_NAME: str = "ISEYAA — Ogun State"

    # Firebase (push)
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_SERVER_KEY: Optional[str] = None

    # Twilio WhatsApp
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: str = "whatsapp:+234XXXXXXXXXX"


@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
