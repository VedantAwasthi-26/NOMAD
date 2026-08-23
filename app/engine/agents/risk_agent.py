"""
Risk & Monitoring Agent -- capabilities 6, 7 (Facility & Route Risk
Monitoring, Multi Location Operations Monitor).

Combines Mireye hazard fields with the live external feeds Vedant already
wired up (Open-Meteo weather, FEMA disaster declarations) into one scored
EvidenceBundle. Also exposes the network-wide comparison (get_multi_location_data)
for the Operations Monitor half of this agent's job.
"""

from __future__ import annotations

from app.services.risk_service import get_risk_data
from app.services.multi_location_service import get_multi_location_data
from app.engine.schemas import EvidenceBundle
from app.engine.scoring import score_hazard_safety, score_live_conditions


async def get_risk_evidence(address: str) -> EvidenceBundle:
    risk = await get_risk_data(address)

    # facility_risks carries the same field names score_hazard_safety
    # already knows how to read (fema_flood_zone, wildfire_annual_frequency,
    # landslide_susceptibility_index, seismic_design_category) -- reused
    # directly rather than duplicating the scoring logic.
    hazard_factor, hazard_gaps = score_hazard_safety(risk.facility_risks, weight=0.5)

    weather_alerts = risk.environmental_risks.get("weather", [])
    disaster_alerts = risk.environmental_risks.get("disaster_alerts", [])
    live_factor, live_gaps = score_live_conditions(weather_alerts, disaster_alerts, weight=0.5)

    return EvidenceBundle(
        address=address,
        lat=risk.lat,
        lng=risk.lng,
        factors=[hazard_factor, live_factor],
        gaps=hazard_gaps + live_gaps,
    )


async def get_network_risk_comparison(addresses: list[str]) -> dict:
    """The Operations Monitor half: compares hazard-relevant fields across
    a whole location network and flags outliers. Vedant's
    multi_location_service already computes min/max/average and a simple
    z-score-style outlier flag -- returned as-is here since it's already
    real, tested aggregation logic, not something to rebuild."""
    data = await get_multi_location_data(addresses)
    return {
        "location_count": len(data.locations),
        "comparative_metrics": data.comparative_metrics,
        "outlier_alerts": data.outlier_alerts,
        "network_insights": data.network_insights,
    }
