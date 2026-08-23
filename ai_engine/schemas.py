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
