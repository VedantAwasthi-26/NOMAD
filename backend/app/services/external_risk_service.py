import httpx

from app.integrations.external.risk import ExternalRiskData


async def get_external_risk_data(
    lat: float,
    lng: float,
) -> ExternalRiskData:

    weather_url = "https://api.open-meteo.com/v1/forecast"

    weather_params = {
        "latitude": lat,
        "longitude": lng,
        "current": "temperature_2m,wind_speed_10m,precipitation",
        "timezone": "auto",
    }

    disaster_url = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"

    disaster_params = {
        "$top": 10,
        "$orderby": "declarationDate desc",
    }

    async with httpx.AsyncClient() as client:
        weather_response = await client.get(
            weather_url,
            params=weather_params,
        )
        weather_response.raise_for_status()
        weather_data = weather_response.json()

        disaster_response = await client.get(
            disaster_url,
            params=disaster_params,
        )
        disaster_response.raise_for_status()
        disaster_data = disaster_response.json()

    return ExternalRiskData(
        weather_alerts=[
            {
                "temperature_2m": weather_data["current"]["temperature_2m"],
                "wind_speed_10m": weather_data["current"]["wind_speed_10m"],
                "precipitation": weather_data["current"]["precipitation"],
            }
        ],
        disaster_alerts=disaster_data.get(
            "DisasterDeclarationsSummaries",
            [],
        ),
        data_quality=[],
    )