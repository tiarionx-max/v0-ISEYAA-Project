"""ISEYAA API Gateway — Redis connection pool"""
import redis.asyncio as aioredis
from app.core.config import settings

_redis = None

async def init_redis():
    global _redis
    _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

async def get_redis():
    if _redis is None:
        await init_redis()
    return _redis

async def close_redis():
    if _redis:
        await _redis.aclose()
