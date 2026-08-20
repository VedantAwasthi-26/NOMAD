import asyncio

from app.services.external_risk_service import get_external_risk_data


async def main():
    result = await get_external_risk_data(
        38.8977,
        -77.0365,
    )

    assert result.weather_alerts is not None
    assert result.disaster_alerts is not None

    print("External risk service test: PASSED")


asyncio.run(main())