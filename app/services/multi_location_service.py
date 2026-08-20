from statistics import mean

from app.integrations.mireye.client import mireye_client
from app.integrations.mireye.mapper import map_mireye_response
from app.integrations.mireye.multi_location import (
    LocationProfile,
    MultiLocationData,
)


def get_field_value(field):
    if isinstance(field, dict):
        value = field.get("value")
        return value if isinstance(value, (int, float)) else None

    return field if isinstance(field, (int, float)) else None


async def get_multi_location_data(
    addresses: list[str],
) -> MultiLocationData:

    locations = []

    fields = [
        "fema_flood_zone",
        "soil_hydrologic_group",
        "nearest_major_road_distance_m",
        "nearest_major_road_class",
        "nearest_substation_distance_m",
        "nearest_substation_max_voltage_kv",
        "county_population",
    ]

    for address in addresses:
        payload = {
            "preset": "site_selection",
            "address": address,
            "fields": fields,
        }

        result = await mireye_client.fetch(payload)
        mapped = map_mireye_response(result)

        locations.append(
            LocationProfile(
                address=address,
                lat=mapped["lat"],
                lng=mapped["lng"],
                fields=mapped["fields"],
                data_quality=mapped.get("partial_failures", []),
            )
        )

    comparative_metrics = {}

    numeric_fields = [
        "nearest_major_road_distance_m",
        "nearest_substation_distance_m",
        "nearest_substation_max_voltage_kv",
        "county_population",
    ]

    for field in numeric_fields:
        values = []

        for location in locations:
            value = get_field_value(
                location.fields.get(field)
            )

            if value is not None:
                values.append(value)

        if values:
            comparative_metrics[field] = {
                "min": min(values),
                "max": max(values),
                "average": mean(values),
            }

    outlier_alerts = []

    for field in numeric_fields:
        values = []

        for location in locations:
            value = get_field_value(
                location.fields.get(field)
            )

            if value is not None:
                values.append((location.address, value))

        if len(values) < 3:
            continue

        numbers = [value for _, value in values]
        avg = mean(numbers)

        for address, value in values:
            if avg != 0 and abs(value - avg) / abs(avg) > 0.5:
                outlier_alerts.append(
                    {
                        "address": address,
                        "field": field,
                        "value": value,
                        "network_average": avg,
                    }
                )

    network_insights = {
        "location_count": len(locations),
        "fields_compared": list(comparative_metrics.keys()),
        "outlier_count": len(outlier_alerts),
    }

    return MultiLocationData(
        locations=locations,
        comparative_metrics=comparative_metrics,
        outlier_alerts=outlier_alerts,
        network_insights=network_insights,
    )