"""
Logistics & Network Agent -- capabilities 11, 12 (Reverse Logistics &
Inventory Transfer, Network-level destination ranking).

Vedant's reverse_logistics_service.py already fetches per-destination
Mireye fields (road + substation proximity) and produces a *placeholder*
ranking: a hand-rolled linear penalty (`100 - min(road/1000,30) -
min(substation/1000,20)`) with no hazard signal and no documented
weighting. This agent keeps his data-fetching as-is -- no reason to
duplicate real Mireye calls -- but replaces the scoring with the same
graded scorers the rest of the engine already uses, and adds a
hazard_safety read per destination (via the Risk agent's data source) so
a nearby-but-flood-prone destination doesn't outrank a slightly farther,
safer one. Like the other specialists, this agent hands back scored
evidence; it does not run the LLM explanation layer itself -- Site
Selection / the Supervisor decide when a narrated explanation is needed.

get_inventory_transfer_evidence() below does the same thing for Vedant's
newer inventory_transfer_service.py -- the many-to-many counterpart to
reverse logistics (multiple sources, multiple destinations), reusing the
same _score_destination() helper.
"""

from __future__ import annotations

import asyncio

from app.services.reverse_logistics_service import get_reverse_logistics_data
from app.services.inventory_transfer_service import get_inventory_transfer_data
from app.services.risk_service import get_risk_data
from ai_engine.schemas import EvidenceBundle
from ai_engine.scoring import (
    apply_hard_floor,
    score_accessibility,
    score_hazard_safety,
    score_infrastructure,
)

# A destination's own three-factor scheme -- distinct from
# SITE_SELECTION_WEIGHTS, since ranking a reverse-logistics destination is
# "can we reliably move goods here, safely" rather than "should we build a
# facility here." Accessibility weighted highest since it's the whole
# point of a reverse-logistics route; hazard_safety still counts (and can
# still trigger the shared hard floor) rather than being dropped.
_DESTINATION_WEIGHTS = {
    "accessibility": 0.4,
    "infrastructure": 0.3,
    "hazard_safety": 0.3,
}


async def _score_destination(address: str, fields: dict) -> dict:
    """Scores one destination. Runs its own get_risk_data() call because
    reverse_logistics_service only fetches road/substation fields, not
    hazard fields -- reusing Risk & Monitoring's data source here rather
    than re-fetching those fields through a second, separate Mireye call
    shape."""
    accessibility_factor, accessibility_gaps = score_accessibility(
        fields, weight=_DESTINATION_WEIGHTS["accessibility"]
    )
    infrastructure_factor, infrastructure_gaps = score_infrastructure(
        fields, weight=_DESTINATION_WEIGHTS["infrastructure"]
    )

    risk = await get_risk_data(address)
    hazard_factor, hazard_gaps = score_hazard_safety(
        risk.facility_risks, weight=_DESTINATION_WEIGHTS["hazard_safety"]
    )

    factors = [accessibility_factor, infrastructure_factor, hazard_factor]
    gaps = accessibility_gaps + infrastructure_gaps + hazard_gaps

    bundle = EvidenceBundle(
        address=address, lat=risk.lat, lng=risk.lng, factors=factors, gaps=gaps
    )
    capped_score, hard_floor_triggered = apply_hard_floor(factors, bundle.overall_score)

    return {
        "address": address,
        "score": capped_score,
        "hard_floor_triggered": hard_floor_triggered,
        "bundle": bundle,
    }


async def get_logistics_evidence(
    origin_address: str, destination_addresses: list[str]
) -> dict:
    """Fetches Vedant's raw reverse-logistics data for the field values,
    then rescoring each destination in parallel with the shared graded
    scorers instead of his placeholder linear formula. Returns a ranked
    list (not a single EvidenceBundle) since this agent compares N
    candidate destinations rather than scoring one location -- the
    Supervisor's 'how should our physical network be optimized' question
    routes here."""

    raw = await get_reverse_logistics_data(origin_address, destination_addresses)

    fields_by_address = {d["address"]: d["fields"] for d in raw.destinations}

    scored = await asyncio.gather(
        *(
            _score_destination(address, fields_by_address.get(address, {}))
            for address in destination_addresses
        )
    )

    ranking = sorted(scored, key=lambda d: d["score"], reverse=True)

    return {
        "origin_address": origin_address,
        "origins": raw.origins,
        "destination_count": len(destination_addresses),
        "ranking": ranking,
        "route_factors": raw.route_factors,
    }


async def get_inventory_transfer_evidence(
    source_addresses: list[str], destination_addresses: list[str]
) -> dict:
    """Many-to-many counterpart to get_logistics_evidence(), for Vedant's
    new inventory_transfer_service (multiple source warehouses to multiple
    candidate destinations). His service fetches every source/destination
    pair and ranks them with the same kind of hazard-blind linear formula
    reverse-logistics used to have, before this file replaced it. Rescored
    the same way here: a destination's own safety/accessibility doesn't
    depend on which source it's paired with, so each unique destination is
    scored once with _score_destination() and ranked -- Vedant's raw
    per-pair transfer_ranking (distance proxy + road/substation only, no
    hazard signal) is still returned as route_factors for reference, but
    the ranking used for a recommendation should be this one."""

    raw = await get_inventory_transfer_data(source_addresses, destination_addresses)

    fields_by_address = {d.address: d.fields for d in raw.destination_locations}

    scored = await asyncio.gather(
        *(
            _score_destination(address, fields_by_address.get(address, {}))
            for address in destination_addresses
        )
    )

    ranking = sorted(scored, key=lambda d: d["score"], reverse=True)

    return {
        "source_addresses": source_addresses,
        "sources": raw.source_locations,
        "destination_count": len(destination_addresses),
        "ranking": ranking,
        "transfer_factors": raw.transfer_factors,
    }
