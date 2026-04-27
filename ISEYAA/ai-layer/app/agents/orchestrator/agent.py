"""
ISEYAA — Distributed Multi-Agent System (MAS)
Orchestrator Agent
==================
The Orchestrator is the central coordinator for all AI agents on the platform.
It receives tasks, plans execution, delegates to specialist agents, and
aggregates results into coherent responses.

Agent Hierarchy:
    OrchestratorAgent
    ├── LGAIntelligenceAgent  — Government analytics, IGR, ministry dashboards
    ├── EventsAgent           — Event setup, scheduling, ticketing automation
    ├── FraudDetectionAgent   — Real-time transaction fraud scoring
    ├── MediaIntelligenceAgent — News aggregation, summarisation, auto-publishing
    ├── ItineraryAgent        — Personalised tourism journey planning
    └── CitizenChatAgent      — Multi-language citizen support (Yoruba/Hausa/English)

PRD Reference: §4.8 AI & Automation Engine, §4.9 Media Intelligence, §5.8 AI/ML Stack
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

import anthropic
import structlog

from ..config import AgentConfig

logger = structlog.get_logger(__name__)


class AgentType(str, Enum):
    LGA_INTELLIGENCE = "lga_intelligence"
    EVENTS           = "events"
    FRAUD_DETECTION  = "fraud_detection"
    MEDIA_INTELLIGENCE = "media_intelligence"
    ITINERARY        = "itinerary"
    CITIZEN_CHAT     = "citizen_chat"


class TaskStatus(str, Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETED  = "completed"
    FAILED     = "failed"
    DELEGATED  = "delegated"


@dataclass
class AgentTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: AgentType = AgentType.CITIZEN_CHAT
    payload: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    agent_trace: List[str] = field(default_factory=list)


@dataclass
class OrchestratorResult:
    task_id: str
    success: bool
    data: Any
    agent_used: AgentType
    processing_time_ms: float
    trace: List[str]
    tokens_used: Optional[int] = None


class OrchestratorAgent:
    """
    Top-level AI coordinator. Routes tasks to specialist agents,
    handles fallbacks, and maintains audit traces for all AI decisions.
    """

    SYSTEM_PROMPT = """You are the ISEYAA AI Orchestrator — the central intelligence 
coordinator for Ogun State's digital operating system. You help 7 million+ citizens, 
vendors, government officials, athletes, and tourists.

Your responsibilities:
1. Analyse incoming tasks and determine the optimal specialist agent to handle them
2. Break complex multi-domain tasks into sub-tasks for parallel processing
3. Synthesise results from multiple agents into coherent, actionable outputs
4. Maintain audit trails for all government-grade decisions
5. Respond in English, Yoruba (Yorùbá), or Hausa based on user preference

Available specialist agents:
- lga_intelligence: LGA-level government analytics, IGR tracking, ministry reports
- events: Event scheduling, ticketing, venue assignment, bracket generation
- fraud_detection: Transaction risk scoring, anomaly detection
- media_intelligence: News aggregation, AI summarisation, auto-publishing
- itinerary: Tourism journey planning with live availability
- citizen_chat: General citizen queries, service navigation, multi-language support

Always provide structured JSON responses for programmatic consumption.
Prioritise accuracy over speed for financial and government decisions.
Never hallucinate data — if data is unavailable, explicitly state it."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)
        self._agents: Dict[AgentType, Any] = {}
        self._task_semaphore = asyncio.Semaphore(config.max_concurrency)

    def register_agent(self, agent_type: AgentType, agent_instance: Any) -> None:
        """Register a specialist agent with the orchestrator."""
        self._agents[agent_type] = agent_instance
        logger.info("agent_registered", agent_type=agent_type.value)

    async def execute(self, task: AgentTask) -> OrchestratorResult:
        """Execute a task — route to specialist or handle directly."""
        start = time.perf_counter()
        task.status = TaskStatus.RUNNING
        task.agent_trace.append(f"[orchestrator] Task {task.id} received — type={task.type.value}")

        async with self._task_semaphore:
            try:
                # Direct routing for well-defined task types
                if task.type in self._agents:
                    specialist = self._agents[task.type]
                    task.agent_trace.append(f"[orchestrator] Delegating to {task.type.value} agent")
                    result_data = await specialist.execute(task)
                else:
                    # Fallback: orchestrator handles via Claude API
                    task.agent_trace.append("[orchestrator] No specialist — handling directly via Claude")
                    result_data = await self._direct_inference(task)

                task.status = TaskStatus.COMPLETED
                task.result = result_data
                task.completed_at = time.time()

                processing_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    "task_completed",
                    task_id=task.id,
                    agent=task.type.value,
                    duration_ms=round(processing_ms, 2),
                )

                return OrchestratorResult(
                    task_id=task.id,
                    success=True,
                    data=result_data,
                    agent_used=task.type,
                    processing_time_ms=processing_ms,
                    trace=task.agent_trace,
                )

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                processing_ms = (time.perf_counter() - start) * 1000
                logger.error("task_failed", task_id=task.id, error=str(e), exc_info=True)
                return OrchestratorResult(
                    task_id=task.id,
                    success=False,
                    data=None,
                    agent_used=task.type,
                    processing_time_ms=processing_ms,
                    trace=task.agent_trace + [f"[error] {str(e)}"],
                )

    async def execute_batch(self, tasks: List[AgentTask]) -> List[OrchestratorResult]:
        """Execute multiple tasks concurrently (respecting semaphore)."""
        return await asyncio.gather(*[self.execute(task) for task in tasks])

    async def stream_response(self, task: AgentTask) -> AsyncGenerator[str, None]:
        """Stream a response token-by-token for real-time chat interfaces."""
        messages = self._build_messages(task)
        async with self.client.messages.stream(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=self.SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def _direct_inference(self, task: AgentTask) -> dict:
        """Handle task directly via Claude API when no specialist agent exists."""
        messages = self._build_messages(task)
        response = await self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=self.SYSTEM_PROMPT,
            messages=messages,
        )
        content = response.content[0].text if response.content else ""
        # Attempt JSON parse for structured responses
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"response": content, "raw": True}

    def _build_messages(self, task: AgentTask) -> List[dict]:
        """Construct the message array for the Claude API call."""
        user_content = json.dumps({
            "task_type": task.type.value,
            "payload": task.payload,
            "context": task.context,
        }, ensure_ascii=False, indent=2)
        return [{"role": "user", "content": user_content}]

    async def health_check(self) -> dict:
        registered_agents = list(self._agents.keys())
        return {
            "orchestrator": "healthy",
            "model": self.config.model,
            "registered_agents": [a.value for a in registered_agents],
            "max_concurrency": self.config.max_concurrency,
        }
