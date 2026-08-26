import asyncio

from app.services.site_selection_service import get_site_selection_data


async def main():
    result = await get_site_selection_data(
        "1600 Pennsylvania Avenue NW, Washington, DC",
        ["1000 5th Ave, New York, NY 10028"],
    )

    assert result.lat is not None
    assert result.lng is not None
    assert result.physical is not None
    assert result.geographic is not None
    assert result.regulatory is not None
    assert result.demographic is not None
    assert result.logistics_proximity is not None
    assert len(result.logistics_proximity) > 0
    assert result.data_quality is not None

    print("Site selection service + proximity test: PASSED")


asyncio.run(main())