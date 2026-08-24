from app.integrations.mireye.client import mireye_client
from app.integrations.mireye.mapper import map_mireye_response
from app.integrations.mireye.regulatory import RegulatoryResult
from app.integrations.external.regulatory import get_regulatory_external_data


async def get_regulatory_data(address: str) -> RegulatoryResult:
    payload = {
        "preset": "site_selection",
        "address": address,
        "fields": [
            "surface_management_agency",
            "special_use_airspace_type",
            "blm_solar_application_land_status",
            "prime_farmland_classification",
            "in_opportunity_zone",
            "opportunity_zone_tract_geoid",
            "in_air_quality_nonattainment",
            "air_quality_nonattainment_pollutants",
            "air_quality_worst_classification",
            "in_air_quality_maintenance",
            "air_quality_maintenance_pollutants",
            "fire_hazard_severity_zone_class",
            "fire_hazard_responsibility_area",
            "in_karst_area",
            "karst_type",
            "karst_exposure_class",
        ],
    }

    result = await mireye_client.fetch(payload)
    mapped = map_mireye_response(result)
    fields = mapped["fields"]

    external_data = await get_regulatory_external_data(
        lat=mapped["lat"],
        lng=mapped["lng"],
    )

    return RegulatoryResult(
        lat=mapped["lat"],
        lng=mapped["lng"],
        regulations={
            "surface_management_agency": fields.get("surface_management_agency"),
            "special_use_airspace_type": fields.get("special_use_airspace_type"),
            "blm_solar_application_land_status": fields.get(
                "blm_solar_application_land_status"
            ),
            "prime_farmland_classification": fields.get(
                "prime_farmland_classification"
            ),
            "in_opportunity_zone": fields.get("in_opportunity_zone"),
            "opportunity_zone_tract_geoid": fields.get(
                "opportunity_zone_tract_geoid"
            ),
        },
        restrictions={
            "in_air_quality_nonattainment": fields.get(
                "in_air_quality_nonattainment"
            ),
            "air_quality_nonattainment_pollutants": fields.get(
                "air_quality_nonattainment_pollutants"
            ),
            "in_air_quality_maintenance": fields.get(
                "in_air_quality_maintenance"
            ),
            "air_quality_maintenance_pollutants": fields.get(
                "air_quality_maintenance_pollutants"
            ),
        },
        environmental_constraints={
            "air_quality_worst_classification": fields.get(
                "air_quality_worst_classification"
            ),
            "fire_hazard_severity_zone_class": fields.get(
                "fire_hazard_severity_zone_class"
            ),
            "fire_hazard_responsibility_area": fields.get(
                "fire_hazard_responsibility_area"
            ),
            "in_karst_area": fields.get("in_karst_area"),
            "karst_type": fields.get("karst_type"),
            "karst_exposure_class": fields.get("karst_exposure_class"),
        },
        data_quality=mapped.get("partial_failures", []),
        external_data=external_data,
    )