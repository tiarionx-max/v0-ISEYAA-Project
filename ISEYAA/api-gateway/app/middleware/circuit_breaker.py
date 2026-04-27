"""ISEYAA — Circuit Breaker Middleware (stub — wired to prometheus in prod)"""
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Full circuit breaker implementation in Sprint 2
        # using tenacity + Redis failure counters
        return await call_next(request)
