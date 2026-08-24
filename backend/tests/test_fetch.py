import asyncio

from app.integrations.mireye.client import mireye_client
from app.integrations.mireye.mapper import map_mireye_response
from app.integrations.mireye.models import LocationData


async def main():
    payload = {
        "preset": "site_selection",
        "address": "1600 Pennsylvania Avenue NW, Washington, DC",
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
    location_data = LocationData(**mapped)

    assert location_data.lat is not None
    assert location_data.lng is not None
    assert "fema_flood_zone" in location_data.fields
    assert "soil_hydrologic_group" in location_data.fields
    assert "nearest_substation_distance_m" in location_data.fields

    print("Mireye feasibility data test: PASSED")


asyncio.run(main())