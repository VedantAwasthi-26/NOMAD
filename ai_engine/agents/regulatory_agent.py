"""
Regulatory & Compliance Agent -- capabilities 3, 4, 9 (Regulatory/Zoning/
Hazard Data Layer, Permitting Research, Central-vs-Local exceptions).

Deterministic evidence only, no LLM here -- this agent's job is to hand a
scored, cited EvidenceBundle to Site Selection / Logistics & Network, not
to narrate anything itself. Only the consumer agents run the explanation
layer, keeping LLM calls to the points that actually face a user.
"""

from __future__ import annotations

from app.services.regulatory_service import get_regulatory_data
from app.services.permit_research_service import get_permit_research
from ai_engine.schemas import DataGap, EvidenceBundle, SourceSystem
from ai_engine.scoring import score_regulatory_fit


def flatten_regulatory_fields(regulatory) -> dict:
    """Vedant's RegulatoryResult buckets fields into regulations /
    restrictions / environmental_constraints; the scorers read flat
    field names regardless of which bucket they arrived in."""
    return {
        **regulatory.regulations,
        **regulatory.restrictions,
        **regulatory.environmental_constraints,
    }


async def get_regulatory_evidence(
    address: str,
    business_type: str = "general commercial",
    intended_use: str = "general commercial operations",
) -> EvidenceBundle:
    regulatory = await get_regulatory_data(address)
    permit = await get_permit_research(address, business_type, intended_use)

    fields = flatten_regulatory_fields(regulatory)
    factor, gaps = score_regulatory_fit(fields)

    # Central-vs-local signal: an opportunity-zone or nonattainment flag
    # is exactly the kind of geography-driven fact that can force a local
    # exception to a standardized company policy -- surfaced as a note on
    # the factor itself rather than a separate LLM judgment call, so it's
    # visible without spending another model call on every request.
    local_exception_notes = []
    if fields.get("in_opportunity_zone"):
        local_exception_notes.append("in an opportunity zone -- may qualify for local incentives")
    if fields.get("in_air_quality_nonattainment"):
        local_exception_notes.append("in an air-quality nonattainment area -- may require local permitting exceptions")

    all_gaps = list(gaps)
    if permit.data_quality:
        all_gaps.extend(
            DataGap(
                field=str(pf.get("field", "unknown")),
                reason=str(pf.get("reason", "permit research data gap")),
                source_system=SourceSystem.MIREYE,
            )
            for pf in permit.data_quality
        )

    # Vedant's new external live-feed lookup (get_regulatory_external_data,
    # meant to land on regulatory.external_data as weather_alerts/
    # outage_alerts). Read defensively with getattr: as of this writing his
    # RegulatoryResult model hasn't been given an external_data field yet,
    # so his service computes it but pydantic silently drops the unknown
    # keyword -- this stays a safe no-op until he adds the field, no crash
    # either way, and it'll start populating automatically once he does.
    external = getattr(regulatory, "external_data", None) or {}
    for alert in external.get("weather_alerts", []):
        local_exception_notes.append(f"active weather alert: {alert}")
    for alert in external.get("outage_alerts", []):
        local_exception_notes.append(f"active outage alert: {alert}")
    for note in external.get("data_quality", []):
        all_gaps.append(
            DataGap(
                field="external_data",
                reason=str(note),
                source_system=SourceSystem.EXTERNAL_WEATHER,
            )
        )

    if local_exception_notes:
        factor.note = ((factor.note + "; ") if factor.note else "") + "; ".join(local_exception_notes)

    return EvidenceBundle(
        address=address,
        lat=regulatory.lat,
        lng=regulatory.lng,
        factors=[factor],
        gaps=all_gaps,
    )
