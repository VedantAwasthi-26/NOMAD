import asyncio

from app.services.inventory_transfer_service import (
    get_inventory_transfer_data,
)


async def main():
    result = await get_inventory_transfer_data(
        [
            "1600 Pennsylvania Avenue NW, Washington, DC",
        ],
        [
            "350 Fifth Avenue, New York, NY",
            "1 Apple Park Way, Cupertino, CA",
        ],
    )

    assert len(result.source_locations) == 1
    assert len(result.destination_locations) == 2
    assert result.transfer_factors is not None
    assert result.data_quality is not None

    print("Inventory transfer service test: PASSED")


asyncio.run(main())