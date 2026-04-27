"""ISEYAA AI Layer — Configuration"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://iseyaa_user:password@localhost:5432/iseyaa_db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 3
    DATABASE_POOL_TIMEOUT: int = 30

    REDIS_URL: str = "redis://localhost:6379/0"
    AWS_REGION: str = "af-south-1"

    # Anthropic
    ANTHROPIC_API_KEY: str = "sk-ant-changeme"
    ANTHROPIC_MODEL: str = "claude-opus-4-20250514"
    ANTHROPIC_MAX_TOKENS: int = 4096
    AI_AGENT_CONCURRENCY: int = 5

    # Google Maps (for ItineraryAgent)
    GOOGLE_MAPS_API_KEY: Optional[str] = None


class AgentConfig:
    def __init__(self, settings: "Settings"):
        self.anthropic_api_key = settings.ANTHROPIC_API_KEY
        self.model = settings.ANTHROPIC_MODEL
        self.max_tokens = settings.ANTHROPIC_MAX_TOKENS
        self.max_concurrency = settings.AI_AGENT_CONCURRENCY


@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
agent_config = AgentConfig(settings)
