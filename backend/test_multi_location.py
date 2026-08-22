import asyncio

from app.services.multi_location_service import get_multi_location_data


async def main():
    result = await get_multi_location_data(
        [
            "1600 Pennsylvania Avenue NW, Washington, DC",
            "1 Apple Park Way, Cupertino, CA",
            "350 Fifth Avenue, New York, NY",
        ]
    )

    assert len(result.locations) == 3

    for location in result.locations:
        assert location.lat is not None
        assert location.lng is not None
        assert location.fields is not None

    print("Multi-location service test: PASSED")


asyncio.run(main())