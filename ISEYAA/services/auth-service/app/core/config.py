"""
ISEYAA Auth Service — Configuration
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://iseyaa_user:password@localhost:5442/iseyaa_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 5
    DATABASE_POOL_TIMEOUT: int = 30

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AWS KMS (for PII encryption)
    AWS_REGION: str = "af-south-1"
    AWS_KMS_KEY_ID: Optional[str] = None

    # KYC Providers
    NIMC_API_KEY: Optional[str] = None
    NIMC_BASE_URL: str = "https://api.nimc.gov.ng/v1"
    BVN_VERIFICATION_API_KEY: Optional[str] = None

    # 2FA
    TOTP_ISSUER: str = "ISEYAA"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
