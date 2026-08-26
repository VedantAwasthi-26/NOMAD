"""
Shared schemas for the AI / decision engine.

These are the contracts everything else in this module is built against:

- FactorScore / EvidenceBundle: the standardized shape every specialist
  agent (Feasibility, Site Selection, Risk, Regulatory, Demand) normalizes
  its raw Mireye-derived data into, before scoring.
- Recommendation: the final output shape returned to the frontend.

Keeping these separate from Vedant's per-endpoint models (FeasibilityResult,
SiteSelectionData, RiskData, ...) is deliberate: his models are "what Mireye
gave us, lightly bucketed." These are "what we decided, and why" -- the
layer this engine owns.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SourceSystem(str, Enum):
    """Where a piece of evidence ultimately came from. Every factor and
    every citation should be tagged with one of these -- this is what
    makes it possible to show 'X% of this recommendation used Mireye
    data' for the demo, and what makes explanations checkable."""

    MIREYE = "mireye"
    EXTERNAL_WEATHER = "external_weather"
    EXTERNAL_DISASTER = "external_disaster"
    EXTERNAL_OUTAGE = "external_outage"
    EXTERNAL_MARKET = "external_market"
    ENTERPRISE = "enterprise"
    DERIVED = "derived"  # computed from other factors, not a raw source


class FactorScore(BaseModel):
    """One scored factor (e.g. hazard_safety) feeding into an overall
    recommendation. This is the standardized evidence schema every
    specialist agent's scoring function returns."""

    factor: str
    raw_value: Optional[Any] = None
    score: float = Field(..., ge=0, le=100)
    weight: float = Field(..., ge=0, le=1)
    contribution: float  # weight * score, computed once and stored
    confidence: float = Field(1.0, ge=0, le=1)
    source_system: SourceSystem
    source_fields: list[str] = Field(default_factory=list)
    note: Optional[str] = None  # e.g. "missing data, defaulted to midpoint"


class DataGap(BaseModel):
    """A field that was missing, failed to resolve, or was defaulted.
    Surfaced directly to the user rather than silently absorbed into a
    score -- this is what the 'flagged gaps' field in every recommendation
    is built from."""

    field: str
    reason: str
    source_system: SourceSystem


class EvidenceBundle(BaseModel):
    """What a specialist agent (Feasibility, Risk, Regulatory, Demand)
    hands back after scoring its slice of the problem. Site Selection
    aggregates several of these."""

    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    factors: list[FactorScore]
    gaps: list[DataGap] = Field(default_factory=list)
    hard_blockers: list[str] = Field(default_factory=list)

    @property
    def overall_score(self) -> float:
        if not self.factors:
            return 0.0
        return round(sum(f.contribution for f in self.factors), 2)

    @property
    def data_completeness(self) -> float:
        """Fraction of expected source fields that actually resolved.
        Used directly for confidence calibration -- see scoring.py."""
        total_fields = sum(len(f.source_fields) for f in self.factors) or 1
        missing_fields = len(self.gaps)
        return max(0.0, round(1 - (missing_fields / total_fields), 2))


class Recommendation(BaseModel):
    """The final, user-facing output. This is the contract Paarth's
    dashboard should be built against."""

    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None

    feasible: Optional[bool] = None
    overall_score: float = Field(..., ge=0, le=100)
    confidence: float = Field(..., ge=0, le=1)

    factor_breakdown: list[FactorScore]
    strengths: list[str] = Field(default_factory=list)
    flagged_gaps: list[DataGap] = Field(default_factory=list)

    hard_floor_triggered: bool = False
    requires_human_review: bool = False

    explanation: Optional[str] = None  # filled in by the LLM explanation node
    verified_groundedness: bool = False  # set True once the verifier passes

    mireye_field_count: int = 0  # how many distinct Mireye fields were used
    mireye_coverage_note: Optional[str] = None


class StartupContext(BaseModel):
    """Persistent, human-confirmed facts about the startup/business asking
    for a recommendation -- carried across requests so agents don't have
    to re-derive things Mireye can't tell them (this business's actual
    intended use, a capability it has already confirmed it needs, etc.).

    Deliberately separate from every other schema here: everything else in
    this file describes a *location* (what Mireye/an agent found there).
    This describes the *business* asking about it. Nothing in the engine
    writes to a StartupContext directly -- it's read-only input, optional
    everywhere it's threaded through (run_site_selection, explain_and_verify),
    so today's behavior with no context supplied is completely unchanged.
    See MemoryUpdateProposal for how a confirmed change is meant to reach
    one of these."""

    startup_id: str
    business_type: Optional[str] = None
    intended_use: Optional[str] = None
    required_capabilities: list[str] = Field(
        default_factory=list,
        description="Confirmed operational needs, e.g. 'cold storage', 'three-phase power'",
    )
    confirmed_facts: dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form confirmed facts not yet promoted to a named field above",
    )
    last_updated: Optional[str] = None  # ISO-8601 timestamp, set by whatever store owns this


class MemoryUpdateProposal(BaseModel):
    """A proposed addition/change to a startup's StartupContext -- what an
    agent emits when it notices something worth confirming with the
    startup directly, most often a DataGap Mireye can't fill but the
    startup itself could answer (the query-based-intake idea: instead of
    just flagging a gap, propose asking about it).

    Deliberately inert: nothing in this engine applies a
    MemoryUpdateProposal to stored data on its own -- `status` starts
    "pending" and stays that way until a human accepts or rejects it
    wherever StartupContext actually lives. This keeps memory writes
    human-confirmed by construction rather than something an LLM could
    silently mutate."""

    startup_id: str
    field: str
    proposed_value: Any
    reason: str
    source_system: SourceSystem = SourceSystem.DERIVED
    confidence: float = Field(0.5, ge=0, le=1)
    status: str = Field("pending", description="pending | confirmed | rejected")


class StartupDataRequest(BaseModel):
    """The mirror image of MemoryUpdateProposal: instead of the AI
    proposing a value for a human to confirm, this is the AI *asking* the
    startup to supply a value it doesn't have at all yet.

    This is what the query-based intake agent (ai_engine/agents/
    intake_agent.py) emits when a startup submits its initial data
    (business_type, intended_use, required_capabilities) and one of those
    required fields is missing or empty -- instead of just letting a bare
    DataGap silently reduce confidence, the intake agent generates one of
    these per missing field so the frontend/user has something concrete
    and specific to answer, before the recommendation ever runs.

    Deliberately inert, same as MemoryUpdateProposal: nothing here writes
    to StartupContext on its own. `status` starts "pending" until the
    startup answers it, at which point the answer is expected to flow back
    in as an updated StartupContext (or a MemoryUpdateProposal, if it's an
    update to something already on file rather than a first-time answer)."""

    startup_id: str
    field: str
    prompt: str = Field(..., description="Human-readable question to show the startup, e.g. 'What type of business is this?'")
    reason: str = Field(..., description="Why this field is needed, e.g. 'required to score regulatory fit accurately'")
    status: str = Field("pending", description="pending | answered")
