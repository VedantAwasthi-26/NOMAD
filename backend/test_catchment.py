import asyncio

from app.services.catchment_service import get_catchment_data


async def main():
    result = await get_catchment_data(
        "1600 Pennsylvania Avenue NW, Washington, DC",
        5.0,
    )

    assert result.lat is not None
    assert result.lng is not None
    assert result.radius_km == 5.0
    assert result.population is not None
    assert result.proximity is not None
    assert result.data_quality is not None

    print("Catchment service test: PASSED")


asyncio.run(main())