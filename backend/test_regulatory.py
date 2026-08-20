import asyncio

from app.services.regulatory_service import get_regulatory_data


async def main():
    result = await get_regulatory_data(
        "1600 Pennsylvania Avenue NW, Washington, DC"
    )

    assert result.lat is not None
    assert result.lng is not None
    assert result.regulations is not None
    assert result.restrictions is not None
    assert result.environmental_constraints is not None
    assert result.data_quality is not None

    print("Regulatory service test: PASSED")


asyncio.run(main())