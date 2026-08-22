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
    destination_ranking = []

    for destination in destinations:
        fields = destination["fields"]

        road_distance = fields.get(
            "nearest_major_road_distance_m"
        )

        substation_distance = fields.get(
            "nearest_substation_distance_m"
        )

        score = 100.0

        if isinstance(road_distance, (int, float)):
            score -= min(road_distance / 1000, 30)

        if isinstance(substation_distance, (int, float)):
            score -= min(substation_distance / 1000, 20)

        destination_ranking.append(
            {
                "address": destination["address"],
                "score": round(max(score, 0), 2),
                "road_distance_m": road_distance,
                "substation_distance_m": substation_distance,
            }
        )

    destination_ranking.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

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