"""
Deterministic scoring engine.

This is the trusted core: plain Python, no LLM, fully unit-testable and
reproducible. Every function here takes raw Mireye-derived fields (using
the real field names confirmed in Vedant's services) and returns a
FactorScore or an EvidenceBundle. The LLM layer (reasoning.py) only ever
explains what these functions decided -- it never overrides a score.

Normalization thresholds below are reasonable, documented starting
defaults -- tune them once you have real example locations to calibrate
against (see ai_engine/tests/test_scoring.py for the fixture set this
was built and checked against).
"""

from __future__ import annotations

from ai_engine.schemas import DataGap, EvidenceBundle, FactorScore, SourceSystem

# ---------------------------------------------------------------------------
# Default weights -- the five factors match the product's own scorecard
# (accessibility, population coverage, regulatory fit, infrastructure,
# hazard safety). Kept as a plain dict so they're trivially overridable
# per-capability or per-client later, per the "fixed defaults to start"
# decision.
# ---------------------------------------------------------------------------

SITE_SELECTION_WEIGHTS = {
    "accessibility": 0.20,
    "population_coverage": 0.20,
    "regulatory_fit": 0.20,
    "infrastructure": 0.20,
    "hazard_safety": 0.20,
}

# Below this hazard_safety score, the hard floor caps the overall score
# and forces human review regardless of how well everything else scored.
HAZARD_HARD_FLOOR_THRESHOLD = 50.0
HARD_FLOOR_CAPPED_SCORE = 40.0

FEASIBILITY_PASS_THRESHOLD = 55.0

# Feasibility only uses 3 of the 5 site-selection factors (no regulatory
# or population data at that stage) -- these weights are renormalized to
# sum to 1.0 across just those three, rather than reusing the 5-factor
# SITE_SELECTION_WEIGHTS (which would only sum to 0.6 here and silently
# cap every feasibility score at 60).
FEASIBILITY_WEIGHTS = {
    "hazard_safety": 0.45,
    "accessibility": 0.30,
    "infrastructure": 0.25,
}


def _get(fields: dict, key: str) -> tuple[object, bool]:
    """Mireye fields sometimes come back as a bare value and sometimes as
    {'value': ..., ...metadata}; this normalizes both. Returns
    (value, was_present) so callers can tell 'field was null' apart from
    'field was missing entirely'."""
    if key not in fields:
        return None, False
    raw = fields[key]
    if isinstance(raw, dict):
        return raw.get("value"), raw.get("value") is not None
    return raw, raw is not None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def resolve_bool_field(fields: dict, key: str) -> bool | None:
    """Normalizes a Mireye boolean-ish field to an actual bool (or None if
    missing). Mireye fields can arrive dict-wrapped ({'value': ...}, see
    `_get` above) and/or as a string ('true'/'false') instead of a native
    bool -- this is the single place that handles both, so a falsy-but-
    truthy value (a non-empty string like "False", or a wrapped dict)
    never gets read as "flag is set" by a plain `if fields.get(key):`
    check elsewhere in the engine. Exported (not `_`-prefixed) so any
    agent reading a raw boolean-ish field directly -- not just the
    scorers here -- uses the same coercion instead of a second, divergent
    implementation."""
    value, present = _get(fields, key)
    if not present:
        return None
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def _score_and_gap(
    factor: str,
    fields: dict,
    field_names: list[str],
    scorer,
    weight: float,
    source_system: SourceSystem = SourceSystem.MIREYE,
    default_score: float = 50.0,
) -> tuple[FactorScore, list[DataGap]]:
    """Shared plumbing: pull the named fields, run `scorer(values) -> score`,
    fall back to a documented default and a DataGap if anything required
    is missing, and package the result as a FactorScore."""
    values = {}
    gaps: list[DataGap] = []
    for name in field_names:
        value, present = _get(fields, name)
        values[name] = value
        if not present:
            gaps.append(
                DataGap(
                    field=name,
                    reason="missing or null from Mireye response",
                    source_system=source_system,
                )
            )

    if len(gaps) == len(field_names):
        # nothing resolved at all -- use the documented default, flag it
        score = default_score
        note = "all source fields missing; defaulted to midpoint score"
    else:
        score = _clamp(scorer(values))
        note = None if not gaps else f"{len(gaps)} of {len(field_names)} source fields missing"

    factor_score = FactorScore(
        factor=factor,
        raw_value=values,
        score=score,
        weight=weight,
        contribution=round(weight * score, 2),
        confidence=round(1 - (len(gaps) / len(field_names)), 2) if field_names else 1.0,
        source_system=source_system,
        source_fields=field_names,
        note=note,
    )
    return factor_score, gaps


# ---------------------------------------------------------------------------
# Individual factor scorers
# ---------------------------------------------------------------------------

_FLOOD_ZONE_SCORES = {
    # FEMA flood zone letter -> safety score (higher = safer)
    "X": 100.0, "X500": 90.0, "B": 80.0, "C": 90.0,
    "A": 30.0, "AE": 25.0, "AH": 35.0, "AO": 40.0,
    "V": 10.0, "VE": 5.0,
}

_SEISMIC_CATEGORY_SCORES = {
    # FEMA/ASCE seismic design category -> safety score
    "A": 100.0, "B": 85.0, "C": 70.0, "D": 45.0, "E": 20.0, "F": 5.0,
}


def score_hazard_safety(
    fields: dict, weight: float = SITE_SELECTION_WEIGHTS["hazard_safety"]
) -> tuple[FactorScore, list[DataGap]]:
    def scorer(v: dict) -> float:
        parts = []

        flood_zone = v.get("fema_flood_zone")
        if flood_zone is not None:
            parts.append(_FLOOD_ZONE_SCORES.get(str(flood_zone).upper(), 50.0))

        wildfire_freq = v.get("wildfire_annual_frequency")
        if isinstance(wildfire_freq, (int, float)):
            # frequency is typically a small probability (e.g. 0.0-0.1);
            # higher frequency -> lower score
            parts.append(_clamp(100 - (wildfire_freq * 1000)))

        landslide_idx = v.get("landslide_susceptibility_index")
        if isinstance(landslide_idx, (int, float)):
            # assume 0 (none) - 1 (severe) scale
            parts.append(_clamp(100 - (landslide_idx * 100)))

        seismic_cat = v.get("seismic_design_category")
        if seismic_cat is not None:
            parts.append(_SEISMIC_CATEGORY_SCORES.get(str(seismic_cat).upper(), 50.0))

        wetland_frac = v.get("wetland_fraction_of_parcel")
        if isinstance(wetland_frac, (int, float)):
            parts.append(_clamp(100 - (wetland_frac * 100)))

        if not parts:
            return 50.0

        # Hazard safety is deliberately "weakest-link"-weighted, not a
        # plain average: one severe hazard indicator (e.g. a coastal
        # flood zone) should drag the score down hard even if the other
        # hazard sub-readings look fine. A plain average lets a single
        # bad signal get diluted into an innocuous-looking number, which
        # is exactly what the hard-floor rule downstream is meant to
        # catch -- so this factor itself needs to already reflect that.
        worst = min(parts)
        average = sum(parts) / len(parts)
        return 0.6 * worst + 0.4 * average

    return _score_and_gap(
        factor="hazard_safety",
        fields=fields,
        field_names=[
            "fema_flood_zone",
            "wildfire_annual_frequency",
            "landslide_susceptibility_index",
            "seismic_design_category",
            "wetland_fraction_of_parcel",
        ],
        scorer=scorer,
        weight=weight,
    )


_ROAD_CLASS_SCORES = {
    "motorway": 100.0, "trunk": 90.0, "primary": 80.0,
    "secondary": 65.0, "tertiary": 50.0, "residential": 30.0,
}


def score_accessibility(
    fields: dict, weight: float = SITE_SELECTION_WEIGHTS["accessibility"]
) -> tuple[FactorScore, list[DataGap]]:
    def scorer(v: dict) -> float:
        parts = []

        road_distance = v.get("nearest_major_road_distance_m")
        if isinstance(road_distance, (int, float)):
            # 0m -> 100, 5000m (5km) or further -> 0, linear between
            parts.append(_clamp(100 - (road_distance / 50)))

        road_class = v.get("nearest_major_road_class")
        if road_class is not None:
            parts.append(_ROAD_CLASS_SCORES.get(str(road_class).lower(), 50.0))

        return sum(parts) / len(parts) if parts else 50.0

    return _score_and_gap(
        factor="accessibility",
        fields=fields,
        field_names=["nearest_major_road_distance_m", "nearest_major_road_class"],
        scorer=scorer,
        weight=weight,
    )


def score_infrastructure(
    fields: dict, weight: float = SITE_SELECTION_WEIGHTS["infrastructure"]
) -> tuple[FactorScore, list[DataGap]]:
    def scorer(v: dict) -> float:
        parts = []

        sub_distance = v.get("nearest_substation_distance_m")
        if isinstance(sub_distance, (int, float)):
            # 0m -> 100, 10000m (10km) or further -> 0
            parts.append(_clamp(100 - (sub_distance / 100)))

        sub_voltage = v.get("nearest_substation_max_voltage_kv")
        if isinstance(sub_voltage, (int, float)):
            # more available voltage capacity -> better; 0kV -> 0, 500kV+ -> 100
            parts.append(_clamp((sub_voltage / 500) * 100))

        soil_group = v.get("soil_hydrologic_group")
        if soil_group is not None:
            # A = best drainage, D = worst
            soil_scores = {"A": 100.0, "B": 75.0, "C": 50.0, "D": 25.0}
            parts.append(soil_scores.get(str(soil_group).upper(), 50.0))

        return sum(parts) / len(parts) if parts else 50.0

    return _score_and_gap(
        factor="infrastructure",
        fields=fields,
        field_names=[
            "nearest_substation_distance_m",
            "nearest_substation_max_voltage_kv",
            "soil_hydrologic_group",
        ],
        scorer=scorer,
        weight=weight,
    )


def score_population_coverage(
    fields: dict, weight: float = SITE_SELECTION_WEIGHTS["population_coverage"]
) -> tuple[FactorScore, list[DataGap]]:
    def scorer(v: dict) -> float:
        population = v.get("county_population")
        if isinstance(population, (int, float)):
            # 0 -> 0, 1,000,000+ -> 100, linear
            return _clamp((population / 1_000_000) * 100)
        return 50.0

    return _score_and_gap(
        factor="population_coverage",
        fields=fields,
        field_names=["county_population"],
        scorer=scorer,
        weight=weight,
    )


def score_live_conditions(
    weather_alerts: list[dict], disaster_alerts: list[dict], weight: float = 0.15
) -> tuple[FactorScore, list[DataGap]]:
    """Risk & Monitoring-specific factor, built from the live external
    feeds (Open-Meteo weather + FEMA disaster declarations) already wired
    up in Vedant's external_risk_service.py. Deliberately separate from
    Mireye-sourced factors -- tagged with its own SourceSystem values so
    it's clear in the evidence trail that this came from live external
    data, not Mireye."""
    gaps: list[DataGap] = []
    score = 100.0

    if not weather_alerts:
        gaps.append(DataGap(field="weather_alerts", reason="no weather data returned",
                             source_system=SourceSystem.EXTERNAL_WEATHER))
    else:
        current = weather_alerts[0]
        precipitation = current.get("precipitation")
        wind = current.get("wind_speed_10m")
        if isinstance(precipitation, (int, float)) and precipitation > 10:
            score -= 20
        if isinstance(wind, (int, float)) and wind > 60:
            score -= 20

    if disaster_alerts is None:
        gaps.append(DataGap(field="disaster_alerts", reason="no disaster feed returned",
                             source_system=SourceSystem.EXTERNAL_DISASTER))
    else:
        # a nonzero recent-disaster count for the region is a soft signal,
        # not a hard blocker -- FEMA's feed here isn't filtered to this
        # exact location, so treat it as informative context, not proof.
        score -= min(len(disaster_alerts) * 2, 20)

    factor = FactorScore(
        factor="live_conditions",
        raw_value={"weather_alerts": weather_alerts, "disaster_count": len(disaster_alerts or [])},
        score=_clamp(score),
        weight=weight,
        contribution=round(weight * _clamp(score), 2),
        confidence=1.0 if not gaps else round(1 - (len(gaps) / 2), 2),
        source_system=SourceSystem.EXTERNAL_WEATHER,
        source_fields=["weather_alerts", "disaster_alerts"],
        note="derived from live Open-Meteo + FEMA feeds, not Mireye" if not gaps else None,
    )
    return factor, gaps


# Regulatory fields that indicate a restriction if truthy/present --
# used as simple penalty flags rather than a graded score, since these
# are mostly boolean/categorical constraints, not a continuum.
_REGULATORY_PENALTY_FIELDS = {
    "in_air_quality_nonattainment": 15.0,
    "in_air_quality_maintenance": 8.0,
    "in_karst_area": 10.0,
    "in_opportunity_zone": -10.0,  # opportunity zones are a *positive* signal
}


def score_regulatory_fit(regulatory_fields: dict) -> tuple[FactorScore, list[DataGap]]:
    """Takes the flattened dict of regulations/restrictions/environmental
    fields from get_regulatory_data() (regulations | restrictions |
    environmental_constraints all merged by the caller)."""

    def scorer(v: dict) -> float:
        score = 100.0
        for field, penalty in _REGULATORY_PENALTY_FIELDS.items():
            if resolve_bool_field(v, field):
                score -= penalty
        fire_zone = v.get("fire_hazard_severity_zone_class")
        if fire_zone is not None and str(fire_zone).lower() in ("high", "very high"):
            score -= 20
        return score

    field_names = list(_REGULATORY_PENALTY_FIELDS.keys()) + ["fire_hazard_severity_zone_class"]
    return _score_and_gap(
        factor="regulatory_fit",
        fields=regulatory_fields,
        field_names=field_names,
        scorer=scorer,
        weight=SITE_SELECTION_WEIGHTS["regulatory_fit"],
    )


# ---------------------------------------------------------------------------
# Aggregate scoring -- Site Selection and Feasibility
# ---------------------------------------------------------------------------

def reweight(factor: FactorScore, new_weight: float) -> FactorScore:
    """Returns a copy of a FactorScore with a different weight/contribution.

    Needed when a specialist agent (e.g. Risk & Monitoring) scores a
    factor using its own internal weighting scheme, but Site Selection
    needs to fold that same factor into its own five-factor weighted
    total (SITE_SELECTION_WEIGHTS) -- the score itself is unchanged, only
    how much it counts toward whichever aggregate is consuming it."""
    updated = factor.model_copy()
    updated.weight = new_weight
    updated.contribution = round(new_weight * factor.score, 2)
    return updated


def apply_hard_floor(factors: list[FactorScore], overall_score: float) -> tuple[float, bool]:
    """The safety net a pure weighted average can't provide: a bad
    hazard_safety reading caps the overall score and forces review,
    no matter how good everything else looks."""
    hazard = next((f for f in factors if f.factor == "hazard_safety"), None)
    if hazard is not None and hazard.score < HAZARD_HARD_FLOOR_THRESHOLD:
        return min(overall_score, HARD_FLOOR_CAPPED_SCORE), True
    return overall_score, False


def score_site_selection(
    address: str,
    site_fields: dict,
    regulatory_fields: dict,
    lat: float | None = None,
    lng: float | None = None,
) -> EvidenceBundle:
    """Combines physical/geographic/demographic fields (from
    get_site_selection_data / get_catchment_data) with regulatory fields
    (from get_regulatory_data) into one scored EvidenceBundle -- the
    direct input to the Site Selection agent's explanation step."""

    factors: list[FactorScore] = []
    gaps: list[DataGap] = []

    for scorer_fn, fields in (
        (score_accessibility, site_fields),
        (score_population_coverage, site_fields),
        (score_infrastructure, site_fields),
        (score_hazard_safety, site_fields),
    ):
        factor, factor_gaps = scorer_fn(fields)
        factors.append(factor)
        gaps.extend(factor_gaps)

    reg_factor, reg_gaps = score_regulatory_fit(regulatory_fields)
    factors.append(reg_factor)
    gaps.extend(reg_gaps)

    return EvidenceBundle(
        address=address,
        lat=lat,
        lng=lng,
        factors=factors,
        gaps=gaps,
    )


# Hard blockers for feasibility -- conditions that disqualify a site
# outright, independent of how the weighted score comes out. This is the
# "Hard Constraints" node from the decision graph.
def find_feasibility_blockers(fields: dict) -> list[str]:
    blockers = []

    flood_zone, present = _get(fields, "fema_flood_zone")
    if present and str(flood_zone).upper() in ("V", "VE"):
        blockers.append(f"fema_flood_zone={flood_zone}: coastal high-hazard zone")

    seismic_cat, present = _get(fields, "seismic_design_category")
    if present and str(seismic_cat).upper() == "F":
        blockers.append(f"seismic_design_category={seismic_cat}: highest seismic risk category")

    wetland_frac, present = _get(fields, "wetland_fraction_of_parcel")
    if present and isinstance(wetland_frac, (int, float)) and wetland_frac > 0.5:
        blockers.append(f"wetland_fraction_of_parcel={wetland_frac}: majority of parcel is wetland")

    return blockers


def score_feasibility(address: str, factors_dict: dict, lat: float | None = None, lng: float | None = None) -> EvidenceBundle:
    """Fills in exactly what Vedant's FeasibilityResult leaves as None:
    `feasible` and `score`. Call this on the `factors` dict returned by
    get_feasibility(), then merge feasible/overall_score back onto the
    FeasibilityResult (see routes/decision.py)."""

    hazard_factor, hazard_gaps = score_hazard_safety(
        factors_dict, weight=FEASIBILITY_WEIGHTS["hazard_safety"]
    )
    access_factor, access_gaps = score_accessibility(
        factors_dict, weight=FEASIBILITY_WEIGHTS["accessibility"]
    )
    infra_factor, infra_gaps = score_infrastructure(
        factors_dict, weight=FEASIBILITY_WEIGHTS["infrastructure"]
    )

    factors = [hazard_factor, access_factor, infra_factor]
    gaps = hazard_gaps + access_gaps + infra_gaps

    blockers = find_feasibility_blockers(factors_dict)

    return EvidenceBundle(
        address=address,
        lat=lat,
        lng=lng,
        factors=factors,
        gaps=gaps,
        hard_blockers=blockers,
    )


def is_feasible(bundle: EvidenceBundle) -> bool:
    if bundle.hard_blockers:
        return False
    return bundle.overall_score >= FEASIBILITY_PASS_THRESHOLD


def confidence_from_completeness(bundle: EvidenceBundle) -> float:
    """Confidence derived from how much of the expected Mireye data
    actually resolved -- the calibration approach decided on, using
    Mireye's own partial-failure signal rather than inventing a separate
    heuristic."""
    return bundle.data_completeness
