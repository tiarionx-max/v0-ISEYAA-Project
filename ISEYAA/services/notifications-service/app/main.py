"""
ISEYAA — Notifications Service
================================
SMS (Termii), Email (SendGrid), Push (FCM), WhatsApp (Twilio).
Consumes AWS SQS queue for async delivery.
Port: 8005
"""
from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from app.core.config import settings
from app.core.database import init_db

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("notifications_service_starting", port=8005)
    await init_db()
    yield
    logger.info("notifications_service_stopped")


app = FastAPI(
    title="ISEYAA Notifications Service",
    description="SMS, Email, Push, WhatsApp notification delivery",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
)

from app.api.v1.notifications_router import router as notifications_router

app.include_router(notifications_router, prefix="/api/v1/notifications", tags=["Notifications"])


@app.get("/health")
async def health():
    return {"service": "notifications-service", "status": "healthy"}
