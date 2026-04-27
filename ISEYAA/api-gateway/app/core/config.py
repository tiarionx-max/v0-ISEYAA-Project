"""
ISEYAA API Gateway — Configuration
===================================
All settings loaded from environment variables via Pydantic Settings.
Secrets resolved from AWS Secrets Manager in production.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ── Core ──────────────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str
    API_GATEWAY_HOST: str = "0.0.0.0"
    API_GATEWAY_PORT: int = 8000
    API_GATEWAY_WORKERS: int = 4

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ── Downstream service URLs ───────────────────────────────────────────────
    AUTH_SERVICE_URL: str = "http://auth-service:8001"
    WALLET_SERVICE_URL: str = "http://wallet-service:8002"
    EVENTS_SERVICE_URL: str = "http://events-service:8003"
    LGA_INTELLIGENCE_SERVICE_URL: str = "http://lga-intelligence-service:8004"
    NOTIFICATIONS_SERVICE_URL: str = "http://notifications-service:8005"
    AI_LAYER_URL: str = "http://ai-layer:8010"

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_RATE_LIMIT_DB: int = 3

    # ── Rate limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_DEFAULT: int = 100
    RATE_LIMIT_AUTH: int = 20
    RATE_LIMIT_PAYMENTS: int = 30
    RATE_LIMIT_AI: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ── AWS ───────────────────────────────────────────────────────────────────
    AWS_REGION: str = "af-south-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SECRETS_MANAGER_PREFIX: str = "iseyaa/prod"

    # ── Observability ─────────────────────────────────────────────────────────
    SENTRY_DSN: Optional[str] = None
    DATADOG_API_KEY: Optional[str] = None
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None

    # ── Circuit breaker ───────────────────────────────────────────────────────
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 30
    CIRCUIT_BREAKER_EXPECTED_EXCEPTION_TYPES: List[str] = ["httpx.ConnectError", "httpx.TimeoutException"]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def service_map(self) -> dict:
        return {
            "auth": self.AUTH_SERVICE_URL,
            "wallet": self.WALLET_SERVICE_URL,
            "events": self.EVENTS_SERVICE_URL,
            "lga": self.LGA_INTELLIGENCE_SERVICE_URL,
            "notifications": self.NOTIFICATIONS_SERVICE_URL,
            "ai": self.AI_LAYER_URL,
        }


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
