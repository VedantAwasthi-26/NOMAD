import asyncio

from app.services.inventory_transfer_service import (
    get_inventory_transfer_data,
)


async def main():
    result = await get_inventory_transfer_data(
        [
            "1600 Pennsylvania Avenue NW, Washington, DC 20500",
        ],
        [
            "1000 5th Ave, New York, NY 10028",
            "1 Apple Park Way, Cupertino, CA 95014",
        ],
    )

    # Source locations
    assert result.source_locations is not None
    assert len(result.source_locations) == 1

    for source in result.source_locations:
        assert source.address
        assert source.lat is not None
        assert source.lng is not None
        assert source.fields is not None
        assert source.data_quality is not None

    # Destination locations
    assert result.destination_locations is not None
    assert len(result.destination_locations) == 2

    for destination in result.destination_locations:
        assert destination.address
        assert destination.lat is not None
        assert destination.lng is not None
        assert destination.fields is not None
        assert destination.data_quality is not None

    # Transfer routes
    assert result.transfer_ranking is not None
    assert len(result.transfer_ranking) == 2

    for ranking in result.transfer_ranking:
        assert ranking["source"]
        assert ranking["destination"]

        route = ranking["route"]

        assert route["origin"]["lat"] is not None
        assert route["origin"]["lng"] is not None
        assert route["destination"]["lat"] is not None
        assert route["destination"]["lng"] is not None

        assert "driving_distance_miles" in route
        assert "driving_distance_km" in route
        assert "driving_duration_minutes" in route
        assert "route_flag" in route

        assert "road_distance_m" in ranking
        assert "substation_distance_m" in ranking

        # Business scoring belongs to the AI layer.
        assert "score" not in ranking

    # Transfer summary
    assert result.transfer_factors is not None
    assert result.transfer_factors["source_count"] == 1
    assert result.transfer_factors["destination_count"] == 2
    assert result.transfer_factors["route_count"] == 2

    # Data-quality tracking
    assert result.data_quality is not None

    print("Opp. 16 inventory transfer end-to-end test: PASSED")


asyncio.run(main())