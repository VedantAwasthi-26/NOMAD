import asyncio

from app.services.permit_research_service import get_permit_research


async def main():
    result = await get_permit_research(
        "1600 Pennsylvania Avenue NW, Washington, DC",
        "retail",
        "commercial retail facility",
    )

    assert result.lat is not None
    assert result.lng is not None
    assert result.zoning is not None
    assert result.permits is not None
    assert result.restrictions is not None
    assert result.application_guidance is not None

    print("Permit research service test: PASSED")


asyncio.run(main())