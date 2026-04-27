"""
ISEYAA — LGA Intelligence Service
===================================
Microservice powering the Government Intelligence Dashboard.
Aggregates cross-module data, generates ministry reports,
IGR analytics, and exposes AI-powered insights for all 20 Ogun State LGAs.

This is a READ-HEAVY service with Redis caching and ClickHouse for OLAP queries.

PRD Reference: §4.11 Government Intelligence Dashboard, §5.5 Database Strategy (ClickHouse)
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.core.config import settings
from app.core.database import init_db
from app.core.clickhouse import init_clickhouse
from app.api.v1 import (
    igr_router, lga_router, ministry_router,
    sports_router, health_router, tourism_router,
    compliance_router, intelligence_router,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("lga_intelligence_service_starting")
    await init_db()
    await init_clickhouse()
    yield
    logger.info("lga_intelligence_service_stopped")


app = FastAPI(
    title="ISEYAA LGA Intelligence Service",
    description=(
        "Government Intelligence Dashboard — IGR analytics, ministry reports, "
        "LGA comparisons, sports data, health utilisation, and AI-powered insights"
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
)

API_V1 = "/api/v1"

# Government dashboard routes (RBAC enforced at API Gateway)
app.include_router(igr_router,          prefix=f"{API_V1}/igr",          tags=["IGR Analytics"])
app.include_router(lga_router,          prefix=f"{API_V1}/lga",          tags=["LGA Data"])
app.include_router(ministry_router,     prefix=f"{API_V1}/ministries",   tags=["Ministry Reports"])
app.include_router(sports_router,       prefix=f"{API_V1}/sports",       tags=["Sports Analytics"])
app.include_router(health_router,       prefix=f"{API_V1}/health-data",  tags=["Health Utilisation"])
app.include_router(tourism_router,      prefix=f"{API_V1}/tourism",      tags=["Tourism Analytics"])
app.include_router(compliance_router,   prefix=f"{API_V1}/compliance",   tags=["Vendor Compliance"])
app.include_router(intelligence_router, prefix=f"{API_V1}/intelligence", tags=["AI Intelligence"])
