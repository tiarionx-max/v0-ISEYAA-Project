"""
ISEYAA — LGA Intelligence Agent
================================
Specialist AI agent for Local Government Area analytics, IGR tracking,
government ministry reporting, and cross-LGA comparison intelligence.

This agent powers the Government Intelligence Dashboard (PRD §4.11).
Supports all 20 LGAs of Ogun State: Abeokuta North, Abeokuta South,
Ado-Odo/Ota, Ewekoro, Ifo, Ijebu East, Ijebu North, Ijebu North East,
Ijebu Ode, Ikenne, Imeko-Afon, Ipokia, Obafemi-Owode, Odeda, Odogbolu,
Ogun Waterside, Remo North, Sagamu, Shagamu (Sagamu), Yewa North, Yewa South.

PRD Reference: §4.11 Government Intelligence Dashboard, §8 Phased Rollout
"""

import json
from typing import Any, Dict, List, Optional

import anthropic
import structlog

from ...config import AgentConfig
from ..orchestrator.agent import AgentTask

logger = structlog.get_logger(__name__)

OGUN_STATE_LGAS = [
    "Abeokuta North", "Abeokuta South", "Ado-Odo/Ota", "Ewekoro",
    "Ifo", "Ijebu East", "Ijebu North", "Ijebu North East", "Ijebu Ode",
    "Ikenne", "Imeko-Afon", "Ipokia", "Obafemi-Owode", "Odeda",
    "Odogbolu", "Ogun Waterside", "Remo North", "Sagamu",
    "Yewa North", "Yewa South",
]

MINISTRIES = [
    "Finance & Economic Planning", "Health", "Education",
    "Sports & Youth Development", "Works & Infrastructure",
    "Agriculture", "Environment", "Commerce & Industry",
    "Tourism, Arts & Culture", "Information & Strategy",
    "Justice", "Women Affairs & Social Development",
]

SYSTEM_PROMPT = """You are the ISEYAA LGA Intelligence Agent — a government-grade 
analytics AI for Ogun State, Nigeria. You provide authoritative intelligence for 
state governance, policy decisions, and ministry operations.

Your capabilities:
- IGR (Internally Generated Revenue) analysis by module, LGA, and ministry
- Cross-LGA performance comparisons and benchmarking
- Sports development participation data by LGA, school, and sport type
- Health service utilisation by region (HMO enrolment, telemedicine, claims)
- Vendor compliance and business licensing statistics
- Predictive analytics for revenue, events, and transport demand
- Tourism analytics: visitor origin, dwell time, accommodation occupancy
- Real-time operational reporting for 20 Ogun State LGAs

Ogun State LGAs: {lgas}
Ministries: {ministries}

Rules:
- Always structure responses as valid JSON
- Flag data gaps explicitly — never fabricate metrics
- All monetary values in Nigerian Naira (₦) unless specified
- Highlight anomalies (spikes, drops >15%) with recommended actions
- Mark projections clearly with confidence intervals
- Comply with NDPA data privacy — no individual PII in reports
""".format(lgas=", ".join(OGUN_STATE_LGAS), ministries=", ".join(MINISTRIES))


class LGAIntelligenceAgent:
    def __init__(self, config: AgentConfig, db_session=None):
        self.config = config
        self.client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)
        self.db = db_session

    async def execute(self, task: AgentTask) -> Dict[str, Any]:
        task.agent_trace.append("[lga_intelligence] Analysing request...")
        action = task.payload.get("action", "general_query")

        handlers = {
            "igr_report":          self._generate_igr_report,
            "lga_comparison":      self._generate_lga_comparison,
            "ministry_dashboard":  self._generate_ministry_dashboard,
            "sports_analytics":    self._generate_sports_analytics,
            "health_utilisation":  self._generate_health_utilisation,
            "tourism_analytics":   self._generate_tourism_analytics,
            "vendor_compliance":   self._generate_vendor_compliance,
            "predictive_forecast": self._generate_predictive_forecast,
            "general_query":       self._general_intelligence_query,
        }

        handler = handlers.get(action, self._general_intelligence_query)
        task.agent_trace.append(f"[lga_intelligence] Executing action: {action}")
        return await handler(task)

    async def _generate_igr_report(self, task: AgentTask) -> Dict[str, Any]:
        """Generate IGR report across all platform modules."""
        period = task.payload.get("period", "monthly")
        lga_filter = task.payload.get("lga")
        module_filter = task.payload.get("module")  # events, marketplace, transport, etc.

        prompt = f"""Generate a detailed IGR analysis report.
Parameters:
- Period: {period}
- LGA Filter: {lga_filter or 'All 20 LGAs'}
- Module Filter: {module_filter or 'All modules'}

Return JSON with this structure:
{{
  "report_type": "igr_analysis",
  "period": "{period}",
  "summary": {{
    "total_igr_ngn": number,
    "period_change_pct": number,
    "top_performing_lga": string,
    "top_performing_module": string
  }},
  "by_module": [
    {{"module": string, "revenue_ngn": number, "transactions": number, "change_pct": number}}
  ],
  "by_lga": [
    {{"lga": string, "revenue_ngn": number, "active_vendors": number, "ranking": number}}
  ],
  "anomalies": [
    {{"lga": string, "module": string, "description": string, "recommended_action": string}}
  ],
  "projections": {{
    "next_period_igr_ngn": number,
    "confidence_interval": {{"low": number, "high": number}},
    "key_drivers": [string]
  }}
}}"""

        return await self._call_claude(prompt, task)

    async def _generate_lga_comparison(self, task: AgentTask) -> Dict[str, Any]:
        """Compare performance across specified LGAs."""
        lgas = task.payload.get("lgas", OGUN_STATE_LGAS[:5])
        metrics = task.payload.get("metrics", ["igr", "vendor_count", "citizen_engagement"])

        prompt = f"""Compare LGA performance across Ogun State.
LGAs to compare: {', '.join(lgas)}
Metrics: {', '.join(metrics)}

Return a ranked comparison JSON with insights and recommended resource allocation."""

        return await self._call_claude(prompt, task)

    async def _generate_ministry_dashboard(self, task: AgentTask) -> Dict[str, Any]:
        ministry = task.payload.get("ministry", "Finance & Economic Planning")
        prompt = f"""Generate a real-time operational dashboard for the {ministry} Ministry.
Include KPIs, alerts, action items, and cross-ministry dependencies.
Return structured JSON suitable for direct dashboard rendering."""
        return await self._call_claude(prompt, task)

    async def _generate_sports_analytics(self, task: AgentTask) -> Dict[str, Any]:
        prompt = """Analyse sports development data across Ogun State.
Include: participation by LGA, school, and sport type; talent pipeline; facility utilisation;
competition results; and funding allocation recommendations.
Return JSON for the Ministry of Sports dashboard."""
        return await self._call_claude(prompt, task)

    async def _generate_health_utilisation(self, task: AgentTask) -> Dict[str, Any]:
        prompt = """Analyse health service utilisation across Ogun State.
Include: HMO enrolment rates, telemedicine usage, claims by region,
hospital capacity, and population health indicators.
Flag underserved LGAs and recommend resource redistribution."""
        return await self._call_claude(prompt, task)

    async def _generate_tourism_analytics(self, task: AgentTask) -> Dict[str, Any]:
        prompt = """Generate tourism analytics for Ogun State.
Include: visitor origin (domestic vs international), dwell time, spend per visit,
accommodation occupancy, top attractions, and seasonal trends.
Reference key sites: Olumo Rock, Oba's Palace, Ogun-Osun River Basin."""
        return await self._call_claude(prompt, task)

    async def _generate_vendor_compliance(self, task: AgentTask) -> Dict[str, Any]:
        prompt = """Generate vendor compliance and business licensing report.
Include: licensed businesses by LGA, pending applications, compliance rates,
enforcement actions, and revenue from licensing fees."""
        return await self._call_claude(prompt, task)

    async def _generate_predictive_forecast(self, task: AgentTask) -> Dict[str, Any]:
        horizon = task.payload.get("horizon_days", 30)
        target = task.payload.get("target", "igr")
        prompt = f"""Generate predictive forecast for {target} over the next {horizon} days.
Use historical platform data patterns. Include confidence intervals,
key assumptions, risk scenarios, and recommended preparatory actions."""
        return await self._call_claude(prompt, task)

    async def _general_intelligence_query(self, task: AgentTask) -> Dict[str, Any]:
        query = task.payload.get("query", "Provide a general state intelligence summary")
        prompt = f"""Government intelligence query: {query}
Context: {json.dumps(task.context, ensure_ascii=False)}
Respond with structured JSON containing findings, recommendations, and data sources."""
        return await self._call_claude(prompt, task)

    async def _call_claude(self, prompt: str, task: AgentTask) -> Dict[str, Any]:
        response = await self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.content[0].text if response.content else "{}"
        task.agent_trace.append(f"[lga_intelligence] Claude response received ({len(content)} chars)")

        try:
            # Strip markdown fences if present
            clean = content.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            return json.loads(clean.strip())
        except json.JSONDecodeError:
            return {"raw_response": content, "parse_error": True}
