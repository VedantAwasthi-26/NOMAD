from app.integrations.mireye.client import mireye_client
from app.integrations.mireye.mapper import map_mireye_response
from app.integrations.mireye.feasibility import FeasibilityResult


async def get_feasibility(address: str) -> FeasibilityResult:
    payload = {
        "preset": "site_selection",
        "address": address,
        "fields": [
            "soil_hydrologic_group",
            "fema_flood_zone",
            "wetland_fraction_of_parcel",
            "nearest_major_road_distance_m",
            "nearest_major_road_class",
            "nearest_substation_distance_m",
            "nearest_substation_max_voltage_kv",
            "wildfire_annual_frequency",
            "landslide_susceptibility_index",
            "seismic_design_category",
        ],
    }

    result = await mireye_client.fetch(payload)
    mapped = map_mireye_response(result)

    return FeasibilityResult(
        lat=mapped["lat"],
        lng=mapped["lng"],
        feasible=None,
        score=None,
        factors=mapped["fields"],
        blockers=[],
        data_quality=mapped.get("partial_failures", []),
    )