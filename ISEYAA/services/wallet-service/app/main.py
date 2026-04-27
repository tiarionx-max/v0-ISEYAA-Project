"""
ISEYAA — Wallet Service
========================
Bank-grade financial core. ACID-compliant, PCI-DSS scoped.
Port: 8002
"""
import asyncio
from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from app.core.config import settings
from app.core.database import init_db

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("wallet_service_starting", port=8002)
    await init_db()
    from app.workers.settlement_worker import SettlementWorker
    asyncio.create_task(SettlementWorker().run())
    yield
    logger.info("wallet_service_stopped")


app = FastAPI(
    title="ISEYAA Wallet Service",
    description="Multi-currency wallets, Paystack/Flutterwave, escrow, IGR revenue split",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
)

from app.api.v1 import wallet_router, transactions_router, paystack_router, escrow_router, payout_router

API_V1 = "/api/v1"
app.include_router(wallet_router,       prefix=f"{API_V1}/wallet",      tags=["Wallet"])
app.include_router(transactions_router, prefix=f"{API_V1}/transactions", tags=["Transactions"])
app.include_router(paystack_router,     prefix=f"{API_V1}/paystack",     tags=["Paystack"])
app.include_router(escrow_router,       prefix=f"{API_V1}/escrow",       tags=["Escrow"])
app.include_router(payout_router,       prefix=f"{API_V1}/payouts",      tags=["Payouts"])


@app.get("/health")
async def health():
    return {"service": "wallet-service", "status": "healthy"}
