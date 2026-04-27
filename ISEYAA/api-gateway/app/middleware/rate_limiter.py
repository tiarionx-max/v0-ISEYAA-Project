"""
ISEYAA — Rate Limiter Middleware (Sliding Window, Redis-backed)
================================================================
Per-user and per-IP rate limiting enforced at API Gateway level.
Different limits for standard, payment, AI, and auth endpoints.

PRD Reference: §6.2 — API rate limiting
"""

import time

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.redis import get_redis

logger = structlog.get_logger(__name__)

# Route-specific rate limits: (requests, window_seconds)
RATE_LIMIT_RULES: list[tuple[str, int, int]] = [
    ("/api/v1/auth/login",    settings.RATE_LIMIT_AUTH,     settings.RATE_LIMIT_WINDOW_SECONDS),
    ("/api/v1/auth/register", settings.RATE_LIMIT_AUTH,     settings.RATE_LIMIT_WINDOW_SECONDS),
    ("/api/v1/wallet",        settings.RATE_LIMIT_PAYMENTS, settings.RATE_LIMIT_WINDOW_SECONDS),
    ("/api/v1/ai",            settings.RATE_LIMIT_AI,        settings.RATE_LIMIT_WINDOW_SECONDS),
]
DEFAULT_LIMIT  = settings.RATE_LIMIT_DEFAULT
DEFAULT_WINDOW = settings.RATE_LIMIT_WINDOW_SECONDS

# Never rate-limit health checks or metrics
EXEMPT_PATHS = {"/api/v1/health", "/metrics", "/"}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if path in EXEMPT_PATHS:
            return await call_next(request)

        limit, window = self._get_limit(path)
        identifier = self._get_identifier(request)
        key = f"rl:{identifier}:{path}"

        redis = await get_redis()
        current, ttl = await self._sliding_window_check(redis, key, window)

        remaining = max(0, limit - current)
        reset_at   = int(time.time()) + (ttl or window)

        if current > limit:
            logger.warning("rate_limit_exceeded", key=key, current=current, limit=limit)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Limit: {limit} per {window}s.",
                    "retry_after": ttl or window,
                },
                headers={
                    "X-RateLimit-Limit":     str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset":     str(reset_at),
                    "Retry-After":           str(ttl or window),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"]     = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"]     = str(reset_at)
        return response

    def _get_limit(self, path: str) -> tuple[int, int]:
        for prefix, limit, window in RATE_LIMIT_RULES:
            if path.startswith(prefix):
                return limit, window
        return DEFAULT_LIMIT, DEFAULT_WINDOW

    def _get_identifier(self, request: Request) -> str:
        # Prefer authenticated user ID; fall back to IP
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        forwarded_for = request.headers.get("X-Forwarded-For")
        ip = forwarded_for.split(",")[0].strip() if forwarded_for else (request.client.host if request.client else "unknown")
        return f"ip:{ip}"

    async def _sliding_window_check(self, redis, key: str, window: int) -> tuple[int, int]:
        """Sliding window counter using Redis INCR + EXPIRE."""
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        results = await pipe.execute()
        count, ttl = results[0], results[1]
        if ttl == -1:  # Key exists but has no TTL (race condition guard)
            await redis.expire(key, window)
        elif count == 1:  # First hit — set TTL
            await redis.expire(key, window)
        return count, max(ttl, 0)
