from app.integrations.mireye.client import mireye_client
from app.integrations.mireye.mapper import map_mireye_response
from app.integrations.mireye.reverse_logistics import ReverseLogisticsData


async def get_reverse_logistics_data(
    origin_address: str,
    destination_addresses: list[str],
) -> ReverseLogisticsData:

    fields = [
        "nearest_major_road_distance_m",
        "nearest_major_road_class",
        "nearest_substation_distance_m",
        "nearest_substation_max_voltage_kv",
    ]

    origins = []
    destinations = []
    data_quality = []

    # Fetch origin data
    result = await mireye_client.fetch({
        "preset": "site_selection",
        "address": origin_address,
        "fields": fields,
    })

    mapped = map_mireye_response(result)

    origins.append({
        "address": origin_address,
        "lat": mapped["lat"],
        "lng": mapped["lng"],
        "fields": mapped["fields"],
    })

    data_quality.extend(mapped.get("partial_failures", []))

    # Fetch destination data
    for address in destination_addresses:
        result = await mireye_client.fetch({
            "preset": "site_selection",
            "address": address,
            "fields": fields,
        })

        mapped = map_mireye_response(result)

        destinations.append({
            "address": address,
            "lat": mapped["lat"],
            "lng": mapped["lng"],
            "fields": mapped["fields"],
        })

        data_quality.extend(mapped.get("partial_failures", []))

    # Get actual driving distance and duration
    proximity_result = None

    try:
        proximity_result = await mireye_client.proximity({
            "op": "distance",
            "origins": [origin_address],
            "destinations": destination_addresses,
            "mode": "driving",
            "units": "miles",
            "max_credits": max(len(destination_addresses) * 14, 1),
        })
    except Exception as exc:
        data_quality.append({
            "field": "proximity",
            "reason": f"Mireye proximity request failed: {exc}",
            "source_system": "mireye",
        })

    proximity_by_index = {
        leg["destination_index"]: leg
        for leg in (proximity_result or {}).get("legs", [])
    }

    destination_ranking = []

    for index, destination in enumerate(destinations):
        fields = destination["fields"]

        road_distance = fields.get(
            "nearest_major_road_distance_m"
        )

        substation_distance = fields.get(
            "nearest_substation_distance_m"
        )

        route = proximity_by_index.get(index, {})

        destination_ranking.append({
            "address": destination["address"],
            "road_distance_m": road_distance,
            "substation_distance_m": substation_distance,
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
        })

    return ReverseLogisticsData(
        origin_address=origin_address,
        destination_addresses=destination_addresses,
        origins=origins,
        destinations=destinations,
        route_factors={
            "origin_count": len(origins),
            "destination_count": len(destinations),
        },
        destination_ranking=destination_ranking,
        data_quality=data_quality,
    )