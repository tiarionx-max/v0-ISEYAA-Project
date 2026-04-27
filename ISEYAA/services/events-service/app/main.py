"""
ISEYAA — Events Service
========================
Full event lifecycle: creation → government approval → ticketing → QR entry.
Port: 8003
"""
from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from app.core.config import settings
from app.core.database import init_db

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("events_service_starting", port=8003)
    await init_db()
    yield
    logger.info("events_service_stopped")


app = FastAPI(
    title="ISEYAA Events Service",
    description="Events, ticketing, QR codes, venues, vendor booths, sponsorship",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
)

from app.api.v1 import events_router, tickets_router, venues_router, sponsors_router

API_V1 = "/api/v1"
app.include_router(events_router,   prefix=f"{API_V1}/events",   tags=["Events"])
app.include_router(tickets_router,  prefix=f"{API_V1}/tickets",  tags=["Tickets"])
app.include_router(venues_router,   prefix=f"{API_V1}/venues",   tags=["Venues"])
app.include_router(sponsors_router, prefix=f"{API_V1}/sponsors", tags=["Sponsorship"])


@app.get("/health")
async def health():
    return {"service": "events-service", "status": "healthy"}
