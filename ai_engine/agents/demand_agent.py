"""
Demand & Market Agent -- capability 10 (Catchment Based Population &
Demand Engine). Built to stand alone deliberately, per the architecture
decision: it's the natural home for the doc's future Market Sizing and
Distribution/Competitor Proximity additions, so keep its evidence
separate from Site Selection rather than inlining it.
"""

from __future__ import annotations

from app.services.catchment_service import get_catchment_data
from ai_engine.schemas import DataGap, EvidenceBundle, SourceSystem
from ai_engine.scoring import score_population_coverage


async def get_demand_evidence(address: str, radius_km: float = 10.0) -> EvidenceBundle:
    catchment = await get_catchment_data(address, radius_km)

    factor, gaps = score_population_coverage(catchment.population)

    # surface the catchment-specific proxy numbers Vedant's service
    # already computes (population density within the requested radius)
    # as extra context on the factor, since they're more specific than
    # the raw county_population figure alone.
    if catchment.demand_estimate.get("population_density_proxy_per_km2") is not None:
        density = catchment.demand_estimate["population_density_proxy_per_km2"]
        factor.note = (
            (factor.note + "; " if factor.note else "")
            + f"~{density:.1f} people/km2 within a {radius_km:.0f}km catchment (proxy estimate)"
        )

    # Vedant's new external market-benchmark lookup (get_market_benchmark,
    # surfaced here as catchment.demand_estimate["market_benchmark"]). It's
    # a stub right now -- always returns None for penetration_rate/
    # demand_multiplier plus a "not_configured" data-quality note -- so
    # this is a no-op today, but wired so the moment he points it at a
    # real source, the multiplier feeds straight into the score with no
    # further changes needed here.
    all_gaps = list(gaps)
    benchmark = catchment.demand_estimate.get("market_benchmark") or {}
    multiplier = benchmark.get("demand_multiplier")
    if multiplier is not None:
        factor.score = max(0.0, min(100.0, factor.score * multiplier))
        factor.contribution = round(factor.score * factor.weight, 4)
        factor.note = (
            (factor.note + "; " if factor.note else "")
            + f"adjusted by external market benchmark (x{multiplier:.2f})"
        )
    for note in benchmark.get("data_quality", []):
        all_gaps.append(
            DataGap(
                field="market_benchmark",
                reason=str(note),
                source_system=SourceSystem.EXTERNAL_MARKET,
            )
        )

    return EvidenceBundle(
        address=address,
        lat=catchment.lat,
        lng=catchment.lng,
        factors=[factor],
        gaps=all_gaps,
    )
