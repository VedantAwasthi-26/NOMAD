from app.integrations.mireye.client import mireye_client
from app.integrations.mireye.mapper import map_mireye_response
from app.integrations.mireye.inventory_transfer import (
    InventoryLocation,
    InventoryTransferData,
)


async def get_inventory_transfer_data(
    source_addresses: list[str],
    destination_addresses: list[str],
) -> InventoryTransferData:

    fields = [
        "nearest_major_road_distance_m",
        "nearest_major_road_class",
        "nearest_substation_distance_m",
        "nearest_substation_max_voltage_kv",
    ]

    sources = []
    destinations = []
    data_quality = []

    for address in source_addresses:
        result = await mireye_client.fetch({
            "preset": "site_selection",
            "address": address,
            "fields": fields,
        })

        mapped = map_mireye_response(result)

        sources.append(
            InventoryLocation(
                address=address,
                lat=mapped["lat"],
                lng=mapped["lng"],
                fields=mapped["fields"],
                data_quality=mapped.get("partial_failures", []),
            )
        )

        data_quality.extend(
            mapped.get("partial_failures", [])
        )

    for address in destination_addresses:
        result = await mireye_client.fetch({
            "preset": "site_selection",
            "address": address,
            "fields": fields,
        })

        mapped = map_mireye_response(result)

        destinations.append(
            InventoryLocation(
                address=address,
                lat=mapped["lat"],
                lng=mapped["lng"],
                fields=mapped["fields"],
                data_quality=mapped.get("partial_failures", []),
            )
        )

        data_quality.extend(
            mapped.get("partial_failures", [])
        )

    transfer_ranking = []

    for source in sources:
        for destination in destinations:

            lat_diff = source.lat - destination.lat
            lng_diff = source.lng - destination.lng

            distance_proxy = (
                (lat_diff ** 2 + lng_diff ** 2) ** 0.5
            )

            road_distance = destination.fields.get(
                "nearest_major_road_distance_m"
            )

            substation_distance = destination.fields.get(
                "nearest_substation_distance_m"
            )

            score = max(
                100 - (distance_proxy * 10),
                0,
            )

            if isinstance(road_distance, (int, float)):
                score -= min(
                    road_distance / 1000,
                    20,
                )

            if isinstance(substation_distance, (int, float)):
                score -= min(
                    substation_distance / 1000,
                    10,
                )

            score = max(score, 0)

            transfer_ranking.append(
                {
                    "source": source.address,
                    "destination": destination.address,
                    "route": {
                        "origin": {
                            "lat": source.lat,
                            "lng": source.lng,
                        },
                        "destination": {
                            "lat": destination.lat,
                            "lng": destination.lng,
                        },
                        "distance_proxy": round(
                            distance_proxy,
                            4,
                        ),
                    },
                    "road_distance_m": road_distance,
                    "substation_distance_m": substation_distance,
                    "score": round(score, 2),
                }
            )

    transfer_ranking.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return InventoryTransferData(
        source_locations=sources,
        destination_locations=destinations,
        transfer_factors={
            "source_count": len(sources),
            "destination_count": len(destinations),
        },
        data_quality=data_quality,
        transfer_ranking=transfer_ranking,
    )