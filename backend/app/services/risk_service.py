from app.integrations.mireye.client import mireye_client
from app.integrations.mireye.mapper import map_mireye_response
from app.integrations.mireye.risk import RiskData
from app.services.external_risk_service import get_external_risk_data


async def get_risk_data(address: str) -> RiskData:
    payload = {
        "preset": "site_selection",
        "address": address,
        "fields": [
            "fema_flood_zone",
            "wildfire_annual_frequency",
            "landslide_susceptibility_index",
            "seismic_design_category",
            "nearest_major_road_distance_m",
            "nearest_major_road_class",
            "nearest_substation_distance_m",
            "nearest_substation_max_voltage_kv",
        ],
    }

    result = await mireye_client.fetch(payload)
    mapped = map_mireye_response(result)

    fields = mapped["fields"]

    external = await get_external_risk_data(
        mapped["lat"],
        mapped["lng"],
    )

    return RiskData(
        lat=mapped["lat"],
        lng=mapped["lng"],
        facility_risks={
            "fema_flood_zone": fields.get("fema_flood_zone"),
            "wildfire_annual_frequency": fields.get(
                "wildfire_annual_frequency"
            ),
            "landslide_susceptibility_index": fields.get(
                "landslide_susceptibility_index"
            ),
            "seismic_design_category": fields.get(
                "seismic_design_category"
            ),
        },
        route_risks={
            "nearest_major_road_distance_m": fields.get(
                "nearest_major_road_distance_m"
            ),
            "nearest_major_road_class": fields.get(
                "nearest_major_road_class"
            ),
        },
        environmental_risks={
            "nearest_substation_distance_m": fields.get(
                "nearest_substation_distance_m"
            ),
            "nearest_substation_max_voltage_kv": fields.get(
                "nearest_substation_max_voltage_kv"
            ),
            "weather": external.weather_alerts,
            "disaster_alerts": external.disaster_alerts,
        },
        data_quality=(
            mapped.get("partial_failures", [])
            + external.data_quality
        ),
    )