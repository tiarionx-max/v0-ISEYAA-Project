"""
ISEYAA — Auth Service
======================
Handles user registration, login, JWT issuance, refresh tokens,
KYC verification, 2FA, biometrics, and RBAC role management.

Port: 8001
PRD Reference: §4.1 User & Identity Management
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.auth_router import router as auth_router
from app.api.v1.kyc_router import router as kyc_router
from app.api.v1.biometric_router import router as biometric_router
from app.api.v1.roles_router import router as roles_router

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("auth_service_starting", port=8001)
    await init_db()
    yield
    logger.info("auth_service_stopped")


app = FastAPI(
    title="ISEYAA Auth Service",
    description="Identity, KYC, biometrics, 2FA, and RBAC for the ISEYAA platform",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    root_path="/api/v1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Gateway handles CORS externally
    allow_methods=["*"],
    allow_headers=["*"],
)

API_V1 = "/api/v1"
app.include_router(auth_router,      prefix=f"{API_V1}/auth",      tags=["Auth"])
app.include_router(kyc_router,       prefix=f"{API_V1}/kyc",       tags=["KYC"])
app.include_router(biometric_router, prefix=f"{API_V1}/biometric", tags=["Biometrics"])
app.include_router(roles_router,     prefix=f"{API_V1}/roles",     tags=["Roles"])


@app.get("/health")
async def health():
    return {"service": "auth-service", "status": "healthy"}
