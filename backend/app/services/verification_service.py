from app.integrations.mireye.client import mireye_client
from app.integrations.mireye.mapper import map_mireye_response
from app.integrations.mireye.models import LocationData


async def verify_address(address: str) -> LocationData:
    payload = {
        "preset": "site_selection",
        "address": address,
        "fields": [
            "parcel_id",
            "parcel_zoning",
            "parcel_area_m2",
            "nearest_major_road_class",
            "nearest_major_road_distance_m",
            "nearest_hospital_distance_m",
            "nearest_school_distance_m",
        ],
    }

    result = await mireye_client.fetch(payload)
    mapped = map_mireye_response(result)

    return LocationData(**mapped)