"""
ISEYAA — API Gateway
====================
Single entry point for all external API traffic.
Handles: routing, auth verification, rate limiting, DDoS protection,
         request logging, circuit breakers, and service discovery.

PRD Reference: §5.1 — API Gateway (AWS API Gateway pattern, self-hosted FastAPI)
"""

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.logging import configure_logging
from app.middleware.auth import JWTVerificationMiddleware
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.circuit_breaker import CircuitBreakerMiddleware
from app.routes import (
    auth_router,
    wallet_router,
    events_router,
    lga_router,
    notifications_router,
    ai_router,
    health_router,
)

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("iseyaa_gateway_starting", version=settings.APP_VERSION, env=settings.ENVIRONMENT)
    # Initialise Redis connection pool
    from app.core.redis import init_redis
    await init_redis()
    yield
    logger.info("iseyaa_gateway_shutting_down")
    from app.core.redis import close_redis
    await close_redis()


app = FastAPI(
    title="ISEYAA API Gateway",
    description=(
        "Ogun State Integrated State Experience, Economy & Automation Platform. "
        "Government-grade digital operating system — API Gateway v1."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# ── Middleware stack (applied bottom-up) ──────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Correlation-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(CircuitBreakerMiddleware)
app.add_middleware(JWTVerificationMiddleware)

# ── Prometheus metrics ─────────────────────────────────────────────────────────
Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/health", "/metrics"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# ── Request timing middleware ──────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"

    logger.info(
        "request_processed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
        request_id=request.state.request_id if hasattr(request.state, "request_id") else None,
    )
    return response


# ── Global exception handlers ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Our team has been notified.",
            "request_id": getattr(request.state, "request_id", str(uuid.uuid4())),
        },
    )


# ── Route registration ─────────────────────────────────────────────────────────
API_V1 = "/api/v1"

app.include_router(health_router,        prefix=f"{API_V1}/health",        tags=["Health"])
app.include_router(auth_router,          prefix=f"{API_V1}/auth",          tags=["Authentication"])
app.include_router(wallet_router,        prefix=f"{API_V1}/wallet",        tags=["Wallet & Payments"])
app.include_router(events_router,        prefix=f"{API_V1}/events",        tags=["Events & Culture"])
app.include_router(lga_router,           prefix=f"{API_V1}/lga",           tags=["LGA Intelligence"])
app.include_router(notifications_router, prefix=f"{API_V1}/notifications", tags=["Notifications"])
app.include_router(ai_router,            prefix=f"{API_V1}/ai",            tags=["AI Agent Layer"])


@app.get("/", include_in_schema=False)
async def root():
    return {
        "platform": "ISEYAA",
        "description": "Ogun State Digital Operating System",
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs",
    }
