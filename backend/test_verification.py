import asyncio

from app.services.verification_service import verify_address


async def main():
    location_data = await verify_address(
        "1600 Pennsylvania Avenue NW, Washington, DC"
    )

    assert location_data.lat is not None
    assert location_data.lng is not None
    assert location_data.fields is not None

    print("Address verification test: PASSED")


asyncio.run(main())