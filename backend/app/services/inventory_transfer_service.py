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
    proximity_result = None

    try:
        proximity_result = await mireye_client.proximity({
            "op": "distance",
            "origins": source_addresses,
            "destinations": destination_addresses,
            "mode": "driving",
            "units": "miles",
            "max_credits": max(
                len(source_addresses)
                * len(destination_addresses)
                * 14,
                1,
            ),
        })
    except Exception as exc:
        data_quality.append({
            "field": "proximity",
            "reason": f"Mireye proximity request failed: {exc}",
            "source_system": "mireye",
        })

    proximity_by_pair = {
        (
            leg["origin_index"],
            leg["destination_index"],
        ): leg
        for leg in (proximity_result or {}).get("legs", [])
    }

    for source_index, source in enumerate(sources):
        for destination_index, destination in enumerate(destinations):

            route = proximity_by_pair.get(
                (source_index, destination_index),
                {},
            )

            road_distance = destination.fields.get(
                "nearest_major_road_distance_m"
            )

            substation_distance = destination.fields.get(
                "nearest_substation_distance_m"
            )

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
                        "driving_distance_miles": route.get(
                            "distance_miles"
                        ),
                        "driving_distance_km": route.get(
                            "distance_km"
                        ),
                        "driving_duration_minutes": route.get(
                            "duration_minutes"
                        ),
                        "route_flag": route.get("flag"),
                    },
                    "road_distance_m": road_distance,
                    "substation_distance_m": substation_distance,
                }
            )

    return InventoryTransferData(
        source_locations=sources,
        destination_locations=destinations,
        transfer_factors={
            "source_count": len(sources),
            "destination_count": len(destinations),
            "route_count": len(transfer_ranking),
        },
        data_quality=data_quality,
        transfer_ranking=transfer_ranking,
    )