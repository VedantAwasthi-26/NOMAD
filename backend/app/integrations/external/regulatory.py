from typing import Any


async def get_regulatory_external_data(
    *,
    lat: float,
    lng: float,
) -> dict[str, Any]:
    return {
        "source": "public_weather_outage_feed",
        "latitude": lat,
        "longitude": lng,
        "weather_alerts": [],
        "outage_alerts": [],
        "data_quality": [
            "external_live_feed_not_configured"
        ],
    }