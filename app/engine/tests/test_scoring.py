"""
Unit tests for the deterministic scoring engine, and the start of the
eval fixture set (good / bad / borderline / incomplete locations).

Run with: pytest app/engine/tests/test_scoring.py -v
"""

from app.engine.scoring import (
    find_feasibility_blockers,
    is_feasible,
    score_feasibility,
    score_site_selection,
    confidence_from_completeness,
)

# ---------------------------------------------------------------------------
# Fixtures -- shaped exactly like the `factors` dict Vedant's
# get_feasibility() returns (mapped["fields"]), using real Mireye field
# names confirmed in his services.
# ---------------------------------------------------------------------------

CLEARLY_GOOD_SITE = {
    "fema_flood_zone": "X",
    "soil_hydrologic_group": "A",
    "wetland_fraction_of_parcel": 0.0,
    "nearest_major_road_distance_m": 200,
    "nearest_major_road_class": "primary",
    "nearest_substation_distance_m": 500,
    "nearest_substation_max_voltage_kv": 230,
    "wildfire_annual_frequency": 0.001,
    "landslide_susceptibility_index": 0.05,
    "seismic_design_category": "B",
}

CLEARLY_BAD_SITE = {
    "fema_flood_zone": "VE",
    "soil_hydrologic_group": "D",
    "wetland_fraction_of_parcel": 0.7,
    "nearest_major_road_distance_m": 9000,
    "nearest_major_road_class": "residential",
    "nearest_substation_distance_m": 15000,
    "nearest_substation_max_voltage_kv": 12,
    "wildfire_annual_frequency": 0.08,
    "landslide_susceptibility_index": 0.9,
    "seismic_design_category": "F",
}

BORDERLINE_SITE = {
    "fema_flood_zone": "A",  # bad hazard signal
    "soil_hydrologic_group": "B",
    "wetland_fraction_of_parcel": 0.1,
    "nearest_major_road_distance_m": 300,  # great accessibility
    "nearest_major_road_class": "motorway",
    "nearest_substation_distance_m": 400,  # great infrastructure
    "nearest_substation_max_voltage_kv": 345,
    "wildfire_annual_frequency": 0.01,
    "landslide_susceptibility_index": 0.15,
    "seismic_design_category": "C",
}

INCOMPLETE_SITE = {
    "fema_flood_zone": "X",
    # everything else missing / failed to resolve
}

REGULATORY_CLEAN = {
    "in_air_quality_nonattainment": False,
    "in_air_quality_maintenance": False,
    "in_karst_area": False,
    "in_opportunity_zone": True,
    "fire_hazard_severity_zone_class": "low",
}

REGULATORY_RESTRICTED = {
    "in_air_quality_nonattainment": True,
    "in_air_quality_maintenance": True,
    "in_karst_area": True,
    "in_opportunity_zone": False,
    "fire_hazard_severity_zone_class": "high",
}


# ---------------------------------------------------------------------------
# Feasibility
# ---------------------------------------------------------------------------

def test_clearly_good_site_is_feasible():
    bundle = score_feasibility("123 Good St", CLEARLY_GOOD_SITE)
    assert is_feasible(bundle) is True
    assert bundle.overall_score > 70
    assert bundle.hard_blockers == []


def test_clearly_bad_site_is_not_feasible():
    bundle = score_feasibility("456 Bad Ave", CLEARLY_BAD_SITE)
    assert is_feasible(bundle) is False
    assert bundle.hard_blockers  # VE flood zone + seismic F + wetland > 0.5 should all trip


def test_hard_blockers_detected_independently_of_score():
    blockers = find_feasibility_blockers(CLEARLY_BAD_SITE)
    assert any("fema_flood_zone" in b for b in blockers)
    assert any("seismic_design_category" in b for b in blockers)
    assert any("wetland_fraction_of_parcel" in b for b in blockers)


def test_incomplete_site_still_scores_but_flags_gaps():
    bundle = score_feasibility("789 Unknown Rd", INCOMPLETE_SITE)
    assert bundle.gaps, "expected missing fields to be recorded as gaps"
    assert confidence_from_completeness(bundle) < 1.0


# ---------------------------------------------------------------------------
# Site Selection + hard floor
# ---------------------------------------------------------------------------

def test_good_site_scores_higher_than_bad_site():
    good = score_site_selection("Good", CLEARLY_GOOD_SITE, REGULATORY_CLEAN)
    bad = score_site_selection("Bad", CLEARLY_BAD_SITE, REGULATORY_RESTRICTED)
    assert good.overall_score > bad.overall_score


def test_hard_floor_caps_score_despite_good_other_factors():
    """This is the specific case the hard-floor rule exists for: great
    accessibility/infrastructure, but a genuinely bad hazard reading --
    the overall score must not be allowed to look good."""
    from app.engine.scoring import apply_hard_floor

    bundle = score_site_selection("Borderline", BORDERLINE_SITE, REGULATORY_CLEAN)
    capped_score, triggered = apply_hard_floor(bundle.factors, bundle.overall_score)

    hazard_factor = next(f for f in bundle.factors if f.factor == "hazard_safety")
    assert hazard_factor.score < 50, "fixture should have a poor hazard score (flood zone A drags down the weakest-link blend)"
    assert triggered is True
    assert capped_score <= 40.0


def test_regulatory_restrictions_lower_the_score():
    clean = score_site_selection("Clean", CLEARLY_GOOD_SITE, REGULATORY_CLEAN)
    restricted = score_site_selection("Restricted", CLEARLY_GOOD_SITE, REGULATORY_RESTRICTED)
    assert restricted.overall_score < clean.overall_score


def test_scoring_is_deterministic_and_repeatable():
    """Same input twice -> identical output. Basic ranking-consistency
    check, run against every scoring change."""
    a = score_site_selection("Repeat", CLEARLY_GOOD_SITE, REGULATORY_CLEAN)
    b = score_site_selection("Repeat", CLEARLY_GOOD_SITE, REGULATORY_CLEAN)
    assert a.overall_score == b.overall_score
