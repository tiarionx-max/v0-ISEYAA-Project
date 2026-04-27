"""
ISEYAA — AI Layer (Distributed Multi-Agent System)
===================================================
Orchestrator + specialist agents powered by Claude Opus 4.
Port: 8010
PRD Reference: §4.8 AI & Automation Engine, §5.8 AI/ML Stack
"""
from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import settings, agent_config
from app.core.database import init_db

logger = structlog.get_logger(__name__)

# Instantiate orchestrator and register agents at startup
orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    logger.info("ai_layer_starting", port=8010, model=settings.ANTHROPIC_MODEL)
    await init_db()

    # Import and wire up the agent hierarchy
    from app.agents.orchestrator.agent import OrchestratorAgent, AgentType
    from app.agents.lga.agent import LGAIntelligenceAgent

    orchestrator = OrchestratorAgent(config=agent_config)
    orchestrator.register_agent(AgentType.LGA_INTELLIGENCE, LGAIntelligenceAgent(config=agent_config))

    # Store on app state so routers can access
    app.state.orchestrator = orchestrator
    logger.info("ai_agents_registered", agents=["lga_intelligence"])
    yield
    logger.info("ai_layer_stopped")


app = FastAPI(
    title="ISEYAA AI Layer",
    description="Multi-Agent System — Orchestrator, LGA Intelligence, Events, Fraud, Media, Itinerary",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
)

from app.api.v1 import ai_router

app.include_router(ai_router, prefix="/api/v1/ai", tags=["AI Agents"])


@app.get("/health")
async def health():
    status = await orchestrator.health_check() if orchestrator else {"status": "initialising"}
    return {"service": "ai-layer", **status}
