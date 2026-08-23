import asyncio

from app.services.decision_engine_service import (
    get_decision_engine_data,
)


async def main():
    result = await get_decision_engine_data(
        "1600 Pennsylvania Avenue NW, Washington, DC"
    )

    assert result.lat is not None
    assert result.lng is not None
    assert result.location_context is not None
    assert result.data_quality is not None

    print("Decision engine service test: PASSED")


asyncio.run(main())