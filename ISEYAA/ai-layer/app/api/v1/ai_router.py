"""ISEYAA AI Layer — API Router"""
from typing import Any, Dict, Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from app.agents.orchestrator.agent import AgentTask, AgentType

router = APIRouter()


class TaskRequest(BaseModel):
    agent_type: str
    payload: Dict[str, Any]
    context: Optional[Dict[str, Any]] = {}


@router.post("/task")
async def run_task(body: TaskRequest, request: Request):
    """Submit a task to the AI orchestrator."""
    orchestrator = request.app.state.orchestrator
    if not orchestrator:
        raise HTTPException(status_code=503, detail="AI layer initialising")
    try:
        agent_type = AgentType(body.agent_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown agent_type: {body.agent_type}")
    task = AgentTask(type=agent_type, payload=body.payload, context=body.context or {})
    result = await orchestrator.execute(task)
    return {
        "task_id": result.task_id,
        "success": result.success,
        "data": result.data,
        "agent": result.agent_used.value,
        "processing_ms": round(result.processing_time_ms, 2),
        "trace": result.trace,
    }


@router.get("/health")
async def ai_health(request: Request):
    orchestrator = request.app.state.orchestrator
    if not orchestrator:
        return {"status": "initialising"}
    return await orchestrator.health_check()
