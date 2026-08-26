"""
Route file for the AI decision engine -- lives in the top-level ai_engine/
package, kept deliberately separate from Vedant's app/ tree so the two
codebases stay easy to tell apart and integrate independently. The only
place this crosses back into app/ is the data-fetching calls below
(app.services.*) and the one wiring line in app/main.py that registers
this router -- everything else here is self-contained.

Wired into app/main.py as:

    from ai_engine.routes.decision import router as decision_router
    app.include_router(decision_router)

Two generations of endpoints live here on purpose:

- /feasibility and /site-selection run the original single-pipeline
  graph.py (hard_constraints -> score -> explain -> END). Kept as-is --
  fully tested, cheap, no fan-out.
- /site-selection/agents, /logistics, /inventory-transfer and /query run
  the confirmed 5-agent + Supervisor + shared-service architecture
  (ai_engine/agents/, ai_engine/supervisor.py). /site-selection/agents is
  the one to demo: it's the actual multi-agent flagship, not the
  single-pipeline stand-in. /inventory-transfer is the many-to-many
  counterpart to /logistics, added once Vedant shipped
  inventory_transfer_service.py.
- /intake is the query-based intake agent: takes a startup's own
  submitted data (business_type, intended_use, required_capabilities),
  not location data, and either confirms it's complete or returns
  specific StartupDataRequests for whatever's missing. It persists what
  it's given (ai_engine/storage.py) -- a startup_id seen before has its
  new answers merged with what's already on file, not overwritten. GET
  /intake/{startup_id} reads back whatever's currently on file with no
  new submission involved.
- /site-selection/agents optionally takes a startup_id alongside address:
  when given, it looks up that startup's stored memory and threads it
  into the explanation/verification layer automatically, so a caller
  doesn't have to resend a startup's confirmed facts on every single
  recommendation request once intake has been done once.
"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.schemas.verification import VerificationRequest
from app.services.feasibility_service import get_feasibility
from app.services.regulatory_service import get_regulatory_data
from app.services.site_selection_service import get_site_selection_data
from ai_engine.schemas import Recommendation, StartupContext, StartupDataRequest
from ai_engine.graph import build_graph
from ai_engine.agents.site_selection_agent import run_site_selection
from ai_engine.agents.logistics_agent import get_logistics_evidence, get_inventory_transfer_evidence
from ai_engine.agents.intake_agent import get_stored_startup_context, intake_startup_data
from ai_engine import supervisor as supervisor_module

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


class SiteSelectionAgentsRequest(BaseModel):
    address: str
    startup_id: Optional[str] = None


@router.post("/site-selection/agents", response_model=Recommendation)
async def decide_site_selection_agents(request: SiteSelectionAgentsRequest):
    """The flagship endpoint for the confirmed architecture: Site
    Selection fans out in parallel to the Regulatory & Compliance, Risk &
    Monitoring, and Demand & Market agents (each backed by the shared
    Foundational Data Service's Mireye fetch), aggregates their evidence
    alongside its own accessibility/infrastructure scoring, applies the
    hard floor, and runs the explanation + verifier loop. This is what
    should be demoed as 'the multi-agent system', not /site-selection
    above (which is the earlier single-pipeline version).

    startup_id is optional and additive: omit it and this behaves exactly
    as before. Pass it and, if that startup has ever completed intake
    (POST /intake), their stored StartupContext is looked up automatically
    and threaded into the explanation/verification layer -- no need to
    resend business_type/intended_use/required_capabilities on every
    single recommendation call once intake's been done once. An unknown
    or never-onboarded startup_id just means no stored context is found,
    which is identical to not passing startup_id at all -- this never
    fails a request just because memory hasn't been built up yet."""
    startup_context = get_stored_startup_context(request.startup_id) if request.startup_id else None
    return await run_site_selection(request.address, startup_context=startup_context)


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


class InventoryTransferRequest(BaseModel):
    source_addresses: list[str]
    destination_addresses: list[str]


@router.post("/inventory-transfer")
async def decide_inventory_transfer(request: InventoryTransferRequest) -> dict:
    """Logistics & Network agent's many-to-many mode, for Vedant's new
    inventory_transfer_service (multiple source warehouses ranking
    multiple candidate destinations). Same graded scorers as /logistics,
    not his hazard-blind distance-proxy formula."""
    return await get_inventory_transfer_evidence(
        request.source_addresses, request.destination_addresses
    )


class IntakeRequest(BaseModel):
    startup_id: str
    business_type: Optional[str] = None
    intended_use: Optional[str] = None
    required_capabilities: list[str] = []
    confirmed_facts: dict[str, Any] = {}


class IntakeResponse(BaseModel):
    complete: bool
    startup_context: StartupContext
    missing: list[StartupDataRequest]


@router.post("/intake", response_model=IntakeResponse)
async def decide_intake(request: IntakeRequest) -> IntakeResponse:
    """Query-based intake agent: merges whatever the startup submitted
    into whatever's already stored for that startup_id (ai_engine/
    storage.py), then checks the result against the three fields
    confirmed over the team's design discussion (business_type,
    intended_use, required_capabilities). `complete=False` means
    `missing` has at least one StartupDataRequest the frontend should
    turn into a follow-up question -- nothing downstream should treat
    this startup_context as ready for scoring until `complete` is True.

    Calling this again later for the same startup_id -- e.g. answering
    one specific StartupDataRequest from a previous call -- fills in just
    that field; it does not need (and should not resend) facts already
    confirmed in an earlier call."""
    context, missing = intake_startup_data(request.model_dump())
    return IntakeResponse(complete=not missing, startup_context=context, missing=missing)


@router.get("/intake/{startup_id}", response_model=StartupContext)
async def get_intake(startup_id: str) -> StartupContext:
    """Read-only: whatever's currently on file for this startup, with no
    new submission involved. 404s for a startup_id that's never completed
    an /intake call -- there's nothing stored to return, as opposed to an
    empty-but-valid StartupContext, which would misleadingly suggest this
    startup was onboarded with nothing confirmed."""
    context = get_stored_startup_context(startup_id)
    if context is None:
        raise HTTPException(status_code=404, detail=f"No stored context for startup_id {startup_id!r}")
    return context


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
