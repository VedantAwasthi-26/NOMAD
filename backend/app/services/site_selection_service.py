from app.integrations.mireye.client import mireye_client
from app.integrations.mireye.mapper import map_mireye_response
from app.integrations.mireye.site_selection import SiteSelectionData


async def get_site_selection_data(address: str) -> SiteSelectionData:
    payload = {
        "preset": "site_selection",
        "address": address,
        "fields": [
            "parcel_area_m2",
            "soil_hydrologic_group",
            "fema_flood_zone",
            "nearest_major_road_distance_m",
            "nearest_major_road_class",
            "nearest_substation_distance_m",
            "nearest_substation_max_voltage_kv",
            "county_population",
        ],
    }

    result = await mireye_client.fetch(payload)
    mapped = map_mireye_response(result)

    fields = mapped["fields"]

    return SiteSelectionData(
        lat=mapped["lat"],
        lng=mapped["lng"],
        physical={
            "parcel_area_m2": fields.get("parcel_area_m2"),
            "soil_hydrologic_group": fields.get("soil_hydrologic_group"),
            "wetland_fraction_of_parcel": fields.get(
                "wetland_fraction_of_parcel"
            ),
            "surface_roughness_class": fields.get(
                "surface_roughness_class"
            ),
        },
        geographic={
            "nearest_major_road_class": fields.get(
                "nearest_major_road_class"
            ),
            "nearest_major_road_distance_m": fields.get(
                "nearest_major_road_distance_m"
            ),
            "nearest_substation_distance_m": fields.get(
                "nearest_substation_distance_m"
            ),
            "nearest_substation_max_voltage_kv": fields.get(
                "nearest_substation_max_voltage_kv"
            ),
            "elevation_m": fields.get("elevation_m"),
            "slope_degrees": fields.get("slope_degrees"),
        },
        regulatory={
            "parcel_zoning": fields.get("parcel_zoning"),
            "fema_flood_zone": fields.get("fema_flood_zone"),
            "in_opportunity_zone": fields.get(
                "in_opportunity_zone"
            ),
            "prime_farmland_classification": fields.get(
                "prime_farmland_classification"
            ),
            "fire_hazard_severity_zone_class": fields.get(
                "fire_hazard_severity_zone_class"
            ),
        },
        demographic={
            "county_population": fields.get("county_population"),
            "county_population_density": fields.get(
                "county_population_density"
            ),
        },
        data_quality=mapped.get("partial_failures", []),
    )