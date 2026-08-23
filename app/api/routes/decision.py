"""
New route file -- does not touch Vedant's existing files, to avoid merge
conflicts. Calls his services directly (same process, same FastAPI app)
and runs the results through the engine.

Add to app/main.py:

    from app.api.routes.decision import router as decision_router
    app.include_router(decision_router)

Two generations of endpoints live here on purpose:

- /feasibility and /site-selection run the original single-pipeline
  graph.py (hard_constraints -> score -> explain -> END). Kept as-is --
  fully tested, cheap, no fan-out.
- /site-selection/agents, /logistics and /query run the confirmed
  5-agent + Supervisor + shared-service architecture (app/engine/agents/,
  app/engine/supervisor.py). /site-selection/agents is the one to demo:
  it's the actual multi-agent flagship, not the single-pipeline stand-in.
"""

from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.schemas.verification import VerificationRequest
from app.services.feasibility_service import get_feasibility
from app.services.regulatory_service import get_regulatory_data
from app.services.site_selection_service import get_site_selection_data
from app.engine.schemas import Recommendation
from app.engine.graph import build_graph
from app.engine.agents.site_selection_agent import run_site_selection
from app.engine.agents.logistics_agent import get_logistics_evidence
from app.engine import supervisor as supervisor_module

router = APIRouter(prefix="/decision", tags=["Decision Engine"])

# Built once at import time; LangGraph graphs are stateless/reusable across requests.
_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = build_graph()
    return _engine


@router.post("/feasibility", response_model=Recommendation)
async def decide_feasibility(request: VerificationRequest):
    """Fills in exactly what get_feasibility() leaves as None: calls
    Vedant's Mireye fetch, then runs the scoring + explanation engine on
    top of it."""
    raw = await get_feasibility(request.address)
    result = _get_engine().invoke(
        {
            "address": request.address,
            "lat": raw.lat,
            "lng": raw.lng,
            "mode": "feasibility",
            "feasibility_fields": raw.factors,
        }
    )
    return result["recommendation"]


@router.post("/site-selection", response_model=Recommendation)
async def decide_site_selection(request: VerificationRequest):
    """Aggregates site selection + regulatory evidence and runs the full
    scoring + explanation engine -- the flagship endpoint."""
    site_data = await get_site_selection_data(request.address)
    regulatory = await get_regulatory_data(request.address)

    # Flatten regulatory's regulations/restrictions/environmental_constraints
    # buckets into one dict, matching what score_regulatory_fit expects.
    regulatory_fields = {
        **regulatory.regulations,
        **regulatory.restrictions,
        **regulatory.environmental_constraints,
    }

    # site_data buckets physical/geographic/regulatory/demographic --
    # flatten physical+geographic+demographic for the site-selection
    # scorers, which read flat field names (nearest_major_road_distance_m,
    # county_population, etc.) regardless of which bucket Vedant put them in.
    site_fields = {
        **site_data.physical,
        **site_data.geographic,
        **site_data.demographic,
    }

    result = _get_engine().invoke(
        {
            "address": request.address,
            "lat": site_data.lat,
            "lng": site_data.lng,
            "mode": "site_selection",
            "site_selection_fields": site_fields,
            "regulatory_fields": regulatory_fields,
        }
    )
    return result["recommendation"]


# ---------------------------------------------------------------------------
# 5-agent + Supervisor + shared-service architecture -- the confirmed
# multi-agent design. These endpoints are additive: they don't replace
# /feasibility or /site-selection above, they run the real agent fan-out.
# ---------------------------------------------------------------------------


@router.post("/site-selection/agents", response_model=Recommendation)
async def decide_site_selection_agents(request: VerificationRequest):
    """The flagship endpoint for the confirmed architecture: Site
    Selection fans out in parallel to the Regulatory & Compliance, Risk &
    Monitoring, and Demand & Market agents (each backed by the shared
    Foundational Data Service's Mireye fetch), aggregates their evidence
    alongside its own accessibility/infrastructure scoring, applies the
    hard floor, and runs the explanation + verifier loop. This is what
    should be demoed as 'the multi-agent system', not /site-selection
    above (which is the earlier single-pipeline version)."""
    return await run_site_selection(request.address)


class LogisticsRequest(BaseModel):
    origin_address: str
    destination_addresses: list[str]


@router.post("/logistics")
async def decide_logistics(request: LogisticsRequest) -> dict:
    """Logistics & Network agent: ranks candidate destinations from an
    origin using the shared graded scorers (accessibility, infrastructure,
    hazard_safety) instead of Vedant's original placeholder linear
    formula. No fixed response_model yet -- this returns a ranked list of
    per-destination FactorScore bundles, not a single Recommendation."""
    return await get_logistics_evidence(request.origin_address, request.destination_addresses)


class SupervisorQueryRequest(BaseModel):
    query: str
    address: Optional[str] = None
    destination_addresses: Optional[list[str]] = None


@router.post("/query")
async def decide_query(request: SupervisorQueryRequest) -> dict[str, Any]:
    """The Supervisor entry point: routes a free-text question to
    whichever of the five agents it resolves to (rule-based fast path,
    LLM fallback for anything the keyword table doesn't recognize), fans
    out in parallel, and returns both the routing decision and the merged
    evidence. This is the concrete implementation of the 'five questions'
    routing table from the architecture doc."""
    return await supervisor_module.handle_query(
        request.query,
        address=request.address,
        destination_addresses=request.destination_addresses,
    )
