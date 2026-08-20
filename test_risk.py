import asyncio

from app.services.risk_service import get_risk_data


async def main():
    result = await get_risk_data(
        "1600 Pennsylvania Avenue NW, Washington, DC"
    )

    assert result.lat is not None
    assert result.lng is not None
    assert result.facility_risks is not None
    assert result.route_risks is not None
    assert result.environmental_risks is not None
    assert result.data_quality is not None

    print("Risk service test: PASSED")


asyncio.run(main())