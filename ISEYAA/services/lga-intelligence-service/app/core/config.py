"""ISEYAA LGA Intelligence Service — Configuration"""
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

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300  # 5-minute cache for dashboard data

    # ClickHouse for OLAP analytics
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_DATABASE: str = "iseyaa_analytics"
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""

    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    AWS_REGION: str = "af-south-1"

    # AI Layer (for intelligence queries)
    AI_LAYER_URL: str = "http://ai-layer:8010"
    ANTHROPIC_API_KEY: Optional[str] = None


@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
