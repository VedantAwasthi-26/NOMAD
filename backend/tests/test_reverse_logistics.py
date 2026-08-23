import asyncio

from app.services.reverse_logistics_service import (
    get_reverse_logistics_data,
)


async def main():
    result = await get_reverse_logistics_data(
        "1600 Pennsylvania Avenue NW, Washington, DC",
        [
            "350 Fifth Avenue, New York, NY",
            "1 Apple Park Way, Cupertino, CA",
        ],
    )

    assert len(result.origins) == 1
    assert len(result.destinations) == 2
    assert result.route_factors is not None
    assert result.data_quality is not None

    print("Reverse logistics service test: PASSED")


asyncio.run(main())