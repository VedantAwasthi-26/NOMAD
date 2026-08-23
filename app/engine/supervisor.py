"""
Supervisor -- the hybrid router from the confirmed architecture: a
rule-based fast path for questions that obviously map to one or more of
the five specialist agents, with an LLM fallback for anything that
doesn't match a known pattern. Routing decisions are returned as a
RouteDecision so routing accuracy can be evaluated separately from the
agents' own output quality (per the "evaluate the router separately"
hardening note in the master guide).

This module intentionally does NOT decide scores or write explanations --
it only decides *which* agent(s) should run for a given natural-language
question, then fans out to them in parallel and returns their combined
evidence. Narration, where it happens, stays inside Site Selection's own
explain_and_verify step; the Supervisor is plumbing, not another voice.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Optional

from pydantic import BaseModel, Field

from app.engine.agents.demand_agent import get_demand_evidence
from app.engine.agents.logistics_agent import get_logistics_evidence
from app.engine.agents.regulatory_agent import get_regulatory_evidence
from app.engine.agents.risk_agent import get_risk_evidence
from app.engine.agents.site_selection_agent import run_site_selection

# ---------------------------------------------------------------------------
# The five agents this Supervisor can route to -- these names are the
# fixed vocabulary both the rule-based path and the LLM fallback have to
# resolve to.
# ---------------------------------------------------------------------------

AGENT_REGULATORY = "regulatory"
AGENT_RISK = "risk"
AGENT_DEMAND = "demand"
AGENT_SITE_SELECTION = "site_selection"
AGENT_LOGISTICS = "logistics"

VALID_AGENTS = {
    AGENT_REGULATORY,
    AGENT_RISK,
    AGENT_DEMAND,
    AGENT_SITE_SELECTION,
    AGENT_LOGISTICS,
}

# Keyword -> agent, used for the rule-based fast path. Deliberately simple
# (substring match on the lowercased query) -- this only needs to catch
# the obvious cases; anything it misses falls through to the LLM.
_AGENT_KEYWORDS = {
    AGENT_REGULATORY: [
        "regulation", "regulatory", "zoning", "zone", "permit", "compliance",
        "restriction", "opportunity zone", "nonattainment", "central-vs-local",
        "exception",
    ],
    AGENT_RISK: [
        "risk", "hazard", "flood", "wildfire", "seismic", "earthquake",
        "disaster", "weather", "monitor", "monitoring", "landslide", "alert",
    ],
    AGENT_DEMAND: [
        "demand", "population", "catchment", "market", "customer base",
        "density",
    ],
    AGENT_SITE_SELECTION: [
        "suitable", "suitability", "feasible", "feasibility", "site selection",
        "expand", "expansion", "candidate", "should we build", "rank this",
    ],
    AGENT_LOGISTICS: [
        "logistics", "route", "routing", "distribution", "inventory",
        "transfer", "reverse logistics", "network optimi", "warehouse",
        "which destination",
    ],
}


class RouteDecision(BaseModel):
    agents: list[str] = Field(..., description="Agent names to invoke, from the fixed five")
    reasoning: str = Field(..., description="Why these agent(s) were chosen")
    used_llm_fallback: bool = False


def rule_based_route(query: str) -> Optional[RouteDecision]:
    """Fast path: keyword match against the five agents. Returns None
    (rather than an empty RouteDecision) when nothing matches, so the
    caller knows to fall back to the LLM router instead of silently
    running zero agents."""
    q = query.lower()
    matched = [
        agent for agent, keywords in _AGENT_KEYWORDS.items()
        if any(kw in q for kw in keywords)
    ]
    if not matched:
        return None
    return RouteDecision(
        agents=matched,
        reasoning=f"Keyword match on: {', '.join(matched)}",
        used_llm_fallback=False,
    )


_ROUTER_SYSTEM_PROMPT = """You are the Supervisor for NOMAD, a site-selection decision support \
system built from five specialist agents:

- regulatory: zoning, permits, environmental/regulatory restrictions, \
  central-vs-local policy exceptions.
- risk: facility and route hazards (flood, wildfire, seismic, landslide), \
  live weather and disaster monitoring, cross-location risk comparison.
- demand: catchment population, demand estimation, market potential \
  around a candidate location.
- site_selection: the flagship suitability check for ONE candidate \
  location -- aggregates regulatory + risk + demand plus its own \
  accessibility/infrastructure scoring into one recommendation.
- logistics: reverse logistics and inventory-transfer destination \
  ranking across MULTIPLE candidate destinations from an origin.

A user question reached you because it didn't obviously match any \
agent's keywords. Decide which agent(s), from exactly these five names, \
should run to answer it. Pick more than one when the question genuinely \
spans concerns (e.g. asking about both suitability and risk). Pick \
site_selection for anything about whether a single place is a good \
choice; pick logistics for anything comparing multiple destinations.

Respond with ONLY a single JSON object, no other text, of exactly this \
shape:
{"agents": ["<agent_name>", "..."], "reasoning": "<why these agent(s)>"}
Use only the five agent names listed above, spelled exactly as shown."""


def _get_llm(temperature: float = 0.0):
    # Imported lazily, same pattern as reasoning.py, so this module stays
    # importable (and rule_based_route testable) without langchain-groq
    # installed.
    from langchain_groq import ChatGroq

    model = os.getenv("NOMAD_ENGINE_MODEL", "openai/gpt-oss-120b")
    return ChatGroq(model=model, temperature=temperature)


def llm_route(query: str) -> RouteDecision:
    """Fallback path for questions the keyword table doesn't recognize.
    Requires langchain-groq + GROQ_API_KEY, same as the explanation layer
    -- not executable in a sandbox without those.

    Calls Groq's plain JSON-object mode directly rather than going through
    LangChain's with_structured_output() -- see the note in
    reasoning._invoke_json_mode for why (that wrapper failed under both
    function_calling and json_mode on the models this project has tried)."""
    llm = _get_llm()
    response = llm.bind(response_format={"type": "json_object"}).invoke(
        [
            {"role": "system", "content": _ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
    )
    decision = RouteDecision.model_validate(json.loads(response.content))
    decision.used_llm_fallback = True
    decision.agents = [a for a in decision.agents if a in VALID_AGENTS]
    if not decision.agents:
        # model returned something outside the fixed five -- degrade to
        # the one agent that can answer almost anything as a last resort,
        # rather than silently running zero agents.
        decision.agents = [AGENT_SITE_SELECTION]
        decision.reasoning += " (fell back to site_selection: no valid agent name returned)"
    return decision


def route(query: str) -> RouteDecision:
    """The hybrid router: try the fast path first, only pay for an LLM
    call when the keyword table genuinely doesn't recognize the
    question. Kept synchronous and separate from dispatch() so routing
    accuracy can be evaluated (e.g. in LangSmith) independently of the
    agents' own output quality."""
    fast = rule_based_route(query)
    if fast is not None:
        return fast
    return llm_route(query)


async def dispatch(
    decision: RouteDecision,
    address: Optional[str] = None,
    destination_addresses: Optional[list[str]] = None,
) -> dict:
    """Fans out to every agent named in the decision, in parallel, and
    returns their evidence keyed by agent name. address is required for
    regulatory/risk/demand/site_selection; destination_addresses (plus
    address as the origin) is required for logistics."""

    calls = {}
    if AGENT_REGULATORY in decision.agents:
        if not address:
            raise ValueError("regulatory agent requires an address")
        calls[AGENT_REGULATORY] = get_regulatory_evidence(address)
    if AGENT_RISK in decision.agents:
        if not address:
            raise ValueError("risk agent requires an address")
        calls[AGENT_RISK] = get_risk_evidence(address)
    if AGENT_DEMAND in decision.agents:
        if not address:
            raise ValueError("demand agent requires an address")
        calls[AGENT_DEMAND] = get_demand_evidence(address)
    if AGENT_SITE_SELECTION in decision.agents:
        if not address:
            raise ValueError("site_selection agent requires an address")
        calls[AGENT_SITE_SELECTION] = run_site_selection(address)
    if AGENT_LOGISTICS in decision.agents:
        if not address or not destination_addresses:
            raise ValueError(
                "logistics agent requires an origin address and destination_addresses"
            )
        calls[AGENT_LOGISTICS] = get_logistics_evidence(address, destination_addresses)

    if not calls:
        return {}

    keys = list(calls.keys())
    results = await asyncio.gather(*(calls[k] for k in keys))
    return dict(zip(keys, results))


async def handle_query(
    query: str,
    address: Optional[str] = None,
    destination_addresses: Optional[list[str]] = None,
) -> dict:
    """The single entry point the API layer should call: route the
    natural-language question, then fan out to whichever agent(s) it
    resolved to. Returns both the routing decision (for transparency and
    for evaluating the router itself) and the merged evidence."""
    decision = route(query)
    results = await dispatch(
        decision, address=address, destination_addresses=destination_addresses
    )
    return {
        "query": query,
        "route": decision.model_dump(),
        "results": results,
    }
