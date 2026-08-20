from app.integrations.mireye.client import mireye_client
from app.integrations.mireye.mapper import map_mireye_response
from app.integrations.mireye.permit_research import PermitResearchData


async def get_permit_research(
    address: str,
    business_type: str,
    intended_use: str,
) -> PermitResearchData:

    payload = {
        "preset": "site_selection",
        "address": address,
        "fields": [
            "parcel_zoning",
            "fema_flood_zone",
            "wetland_fraction_of_parcel",
            "soil_hydrologic_group",
        ],
    }

    result = await mireye_client.fetch(payload)
    mapped = map_mireye_response(result)
    fields = mapped["fields"]

    application_guidance = {
        "business_type": business_type,
        "intended_use": intended_use,
        "steps": [
            "Confirm applicable zoning classification",
            "Identify required permits for the intended use",
            "Review site-specific restrictions",
            "Submit required permit applications to the relevant authority",
        ],
    }

    return PermitResearchData(
        lat=mapped["lat"],
        lng=mapped["lng"],
        zoning={
            "parcel_zoning": fields.get("parcel_zoning"),
        },
        permits={
            "business_type": business_type,
            "intended_use": intended_use,
        },
        restrictions={
            "fema_flood_zone": fields.get("fema_flood_zone"),
            "wetland_fraction_of_parcel": fields.get(
                "wetland_fraction_of_parcel"
            ),
            "soil_hydrologic_group": fields.get(
                "soil_hydrologic_group"
            ),
        },
        application_guidance=application_guidance,
        data_quality=mapped.get("partial_failures", []),
    )