import asyncio

from app.services.feasibility_service import get_feasibility


async def main():
    result = await get_feasibility(
        "1600 Pennsylvania Avenue NW, Washington, DC"
    )

    assert result.lat is not None
    assert result.lng is not None
    assert result.factors is not None
    assert result.feasible is None
    assert result.score is None

    print("Feasibility service test: PASSED")


asyncio.run(main())