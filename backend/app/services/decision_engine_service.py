from app.integrations.mireye.client import mireye_client
from app.integrations.mireye.mapper import map_mireye_response
from app.integrations.mireye.decision_engine import DecisionEngineData


async def get_decision_engine_data(
    address: str,
) -> DecisionEngineData:

    payload = {
        "preset": "site_selection",
        "address": address,
        "fields": [
            "parcel_zoning",
            "fema_flood_zone",
            "soil_hydrologic_group",
            "wetland_fraction_of_parcel",
            "nearest_major_road_distance_m",
            "nearest_major_road_class",
            "nearest_substation_distance_m",
            "nearest_substation_max_voltage_kv",
            "county_population",
        ],
    }

    result = await mireye_client.fetch(payload)
    mapped = map_mireye_response(result)

    return DecisionEngineData(
        address=address,
        lat=mapped["lat"],
        lng=mapped["lng"],
        location_context=mapped["fields"],
        data_quality=mapped.get("partial_failures", []),
    )