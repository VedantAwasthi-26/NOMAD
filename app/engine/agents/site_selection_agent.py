"""
Site Selection Agent -- the flagship (capabilities 2, 8). Aggregates
evidence from the three specialist agents (Regulatory & Compliance, Risk
& Monitoring, Demand & Market) plus its own accessibility/infrastructure
scoring, applies the hard floor, and is the one agent in this set that
actually runs the LLM explanation + verifier layer -- the specialists
hand it deterministic evidence, it's the one that has to justify a call
to a human.
"""

from __future__ import annotations

import asyncio
import logging

from app.services.site_selection_service import get_site_selection_data
from app.engine.agents.regulatory_agent import get_regulatory_evidence
from app.engine.agents.risk_agent import get_risk_evidence
from app.engine.agents.demand_agent import get_demand_evidence
from app.engine.schemas import DataGap, EvidenceBundle, FactorScore, Recommendation, SourceSystem
from app.engine.scoring import (
    apply_hard_floor,
    confidence_from_completeness,
    reweight,
    score_accessibility,
    score_infrastructure,
    SITE_SELECTION_WEIGHTS,
)
from app.engine.reasoning import explain_and_verify

logger = logging.getLogger(__name__)


def _degraded_factor(factor_name: str, weight: float, error: BaseException) -> tuple[FactorScore, DataGap]:
    """Stand-in for a specialist agent's factor when that agent's own
    external call failed (a live Mireye/weather/etc timeout or 5xx --
    the kind of transient failure a single flaky upstream service can
    throw at any moment). Defaults to a neutral, zero-confidence score
    rather than crashing the whole Site Selection request -- one agent
    hiccuping shouldn't take down the other two agents' real evidence.
    Confidence=0 on this factor drags down the overall confidence via
    data_completeness, and the caller forces requires_human_review=True
    whenever any factor was degraded like this."""
    note = (
        f"Could not be scored -- the {factor_name.replace('_', ' ')} agent's "
        f"external call failed ({error.__class__.__name__}: {error}). Defaulted "
        f"to a neutral score; this recommendation's confidence and "
        f"requires_human_review reflect that gap."
    )
    logger.warning("site_selection: degraded factor %s -- %s", factor_name, note)
    factor = FactorScore(
        factor=factor_name,
        raw_value=None,
        score=50.0,
        weight=weight,
        contribution=round(weight * 50.0, 2),
        confidence=0.0,
        source_system=SourceSystem.DERIVED,
        source_fields=[],
        note=note,
    )
    gap = DataGap(
        field=factor_name,
        reason=f"agent call failed: {error.__class__.__name__}: {error}",
        source_system=SourceSystem.DERIVED,
    )
    return factor, gap


async def run_site_selection(address: str) -> Recommendation:
    """One call fans out to all three specialist agents in parallel, then
    aggregates. This is the concrete implementation of the Supervisor
    diagram's 'Where should we expand?' fan-out pattern for a single
    address.

    site_data (the shared Foundational Data Service's own fetch) is load-
    bearing -- lat/lng and the accessibility/infrastructure fields all
    come from it -- so a failure there still fails the whole request.
    A failure in any of the three *specialist* agents degrades gracefully
    instead: that one factor gets a neutral, zero-confidence placeholder
    and a flagged gap, the other two agents' real evidence is still used,
    and requires_human_review is forced True so a human knows to check
    the gap before trusting the recommendation."""

    site_data, regulatory_evidence, risk_evidence, demand_evidence = await asyncio.gather(
        get_site_selection_data(address),
        get_regulatory_evidence(address),
        get_risk_evidence(address),
        get_demand_evidence(address),
        return_exceptions=True,
    )

    if isinstance(site_data, BaseException):
        # Foundational data -- no lat/lng, no accessibility/infrastructure
        # fields, nothing meaningful to score. Re-raise rather than fake it.
        raise site_data

    degraded = False
    all_gaps: list[DataGap] = []

    geographic_fields = site_data.geographic
    accessibility_factor, accessibility_gaps = score_accessibility(geographic_fields)
    infrastructure_factor, infrastructure_gaps = score_infrastructure(geographic_fields)
    all_gaps += accessibility_gaps + infrastructure_gaps

    if isinstance(risk_evidence, BaseException):
        degraded = True
        hazard_factor, hazard_gap = _degraded_factor(
            "hazard_safety", SITE_SELECTION_WEIGHTS["hazard_safety"], risk_evidence
        )
        all_gaps.append(hazard_gap)
        extra_factors: list[FactorScore] = []
    else:
        # regulatory_fit and population_coverage already carry the correct
        # site-selection weight from their own scorers -- only hazard_safety
        # needs reweighting, since Risk & Monitoring scores it with its own
        # internal (0.5/0.5) split against live_conditions.
        hazard_factor = next(f for f in risk_evidence.factors if f.factor == "hazard_safety")
        hazard_factor = reweight(hazard_factor, SITE_SELECTION_WEIGHTS["hazard_safety"])
        live_conditions_factor = next(
            (f for f in risk_evidence.factors if f.factor == "live_conditions"), None
        )
        # live_conditions is real, useful evidence (live weather/disaster
        # feeds) but isn't one of the five scorecard factors -- shown for
        # transparency with weight 0 so it doesn't silently distort the
        # weighted total.
        extra_factors = [reweight(live_conditions_factor, 0.0)] if live_conditions_factor else []
        all_gaps += risk_evidence.gaps

    if isinstance(regulatory_evidence, BaseException):
        degraded = True
        regulatory_factor, regulatory_gap = _degraded_factor(
            "regulatory_fit", SITE_SELECTION_WEIGHTS["regulatory_fit"], regulatory_evidence
        )
        all_gaps.append(regulatory_gap)
    else:
        regulatory_factor = regulatory_evidence.factors[0]
        all_gaps += regulatory_evidence.gaps

    if isinstance(demand_evidence, BaseException):
        degraded = True
        demand_factor, demand_gap = _degraded_factor(
            "population_coverage", SITE_SELECTION_WEIGHTS["population_coverage"], demand_evidence
        )
        all_gaps.append(demand_gap)
    else:
        demand_factor = demand_evidence.factors[0]
        all_gaps += demand_evidence.gaps

    factors = [
        accessibility_factor,
        demand_factor,
        regulatory_factor,
        infrastructure_factor,
        hazard_factor,
    ]

    bundle = EvidenceBundle(
        address=address,
        lat=site_data.lat,
        lng=site_data.lng,
        factors=factors,
        gaps=all_gaps,
    )

    overall_score = bundle.overall_score
    capped_score, hard_floor_triggered = apply_hard_floor(factors, overall_score)
    confidence = confidence_from_completeness(bundle)

    strengths = [
        f.factor.replace("_", " ")
        for f in sorted(factors, key=lambda f: f.score, reverse=True)[:2]
        if f.score >= 70
    ]

    mireye_fields_used = sorted({field for f in factors for field in f.source_fields})

    recommendation = Recommendation(
        address=address,
        lat=site_data.lat,
        lng=site_data.lng,
        feasible=None,  # site selection ranks candidates; feasibility is a separate, stricter check
        overall_score=capped_score,
        confidence=confidence,
        factor_breakdown=factors + extra_factors,
        strengths=strengths,
        flagged_gaps=all_gaps,
        hard_floor_triggered=hard_floor_triggered,
        requires_human_review=hard_floor_triggered or degraded,
        mireye_field_count=len(mireye_fields_used),
        mireye_coverage_note=(
            f"This recommendation drew on {len(mireye_fields_used)} Mireye fields "
            f"across {sum(1 for f in factors if f.source_system.value == 'mireye')} of "
            f"{len(factors)} scored factors: {', '.join(mireye_fields_used)}"
            + (
                " -- NOTE: one or more specialist agents failed and were "
                "defaulted to a neutral placeholder; see flagged_gaps."
                if degraded
                else ""
            )
        ),
    )

    return explain_and_verify(recommendation)
