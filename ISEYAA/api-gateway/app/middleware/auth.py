"""
ISEYAA — JWT Verification Middleware
=====================================
Validates Bearer tokens on every protected request.
Public routes bypass verification. Government and financial
routes enforce 2FA-verified tokens.

PRD Reference: §4.1 — Auth, §6.2 — RBAC, 2FA enforcement
"""

import re
from typing import Optional, Set

import jwt
import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Routes that bypass JWT verification entirely
PUBLIC_ROUTES: Set[str] = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/metrics",
    "/api/v1/health",
    "/api/v1/health/deep",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/auth/verify-email",
    "/api/v1/payments/paystack/webhook",   # Webhook must bypass (HMAC verified separately)
    "/api/v1/payments/flutterwave/webhook",
}

# Routes requiring 2FA-verified tokens (financial + government)
REQUIRES_2FA: tuple = (
    "/api/v1/wallet/transfer",
    "/api/v1/wallet/withdraw",
    "/api/v1/wallet/admin",
    "/api/v1/lga/reports",
    "/api/v1/lga/intelligence",
    "/api/v1/admin",
)

# Minimum roles for government dashboard routes
GOVERNMENT_ROUTES_PREFIX = "/api/v1/lga"


class JWTVerificationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Bypass public routes
        if path in PUBLIC_ROUTES or path.startswith("/api/v1/auth/oauth"):
            return await call_next(request)

        # Extract token
        token = self._extract_token(request)
        if not token:
            return self._unauthorized("Missing or malformed Authorization header.")

        # Verify token
        payload = self._verify_token(token)
        if not payload:
            return self._unauthorized("Invalid or expired token.")

        # 2FA check for sensitive routes
        if any(path.startswith(route) for route in REQUIRES_2FA):
            if not payload.get("two_fa_verified"):
                return self._forbidden("This endpoint requires 2FA verification. Please complete 2FA.")

        # Government route role check
        if path.startswith(GOVERNMENT_ROUTES_PREFIX):
            role = payload.get("role", "citizen")
            if role not in ("government_officer", "ministry_admin", "super_admin"):
                return self._forbidden("Insufficient permissions for government intelligence endpoints.")

        # Attach user context to request state
        request.state.user_id = payload.get("sub")
        request.state.user_role = payload.get("role", "citizen")
        request.state.user_lga = payload.get("lga")
        request.state.two_fa_verified = payload.get("two_fa_verified", False)
        request.state.membership_tier = payload.get("membership_tier", "free")

        return await call_next(request)

    def _extract_token(self, request: Request) -> Optional[str]:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None

    def _verify_token(self, token: str) -> Optional[dict]:
        try:
            return jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_exp": True},
            )
        except jwt.ExpiredSignatureError:
            logger.warning("jwt_token_expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning("jwt_token_invalid", error=str(e))
            return None

    def _unauthorized(self, message: str) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "message": message},
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _forbidden(self, message: str) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={"error": "forbidden", "message": message},
        )
