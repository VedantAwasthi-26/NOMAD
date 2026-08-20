from app.integrations.mireye.client import mireye_client
from app.integrations.mireye.mapper import map_mireye_response
from app.integrations.mireye.catchment import CatchmentData


async def get_catchment_data(
    address: str,
    radius_km: float,
) -> CatchmentData:

    payload = {
        "preset": "site_selection",
        "address": address,
        "fields": [
            "county_population",
            "nearest_major_road_distance_m",
            "nearest_major_road_class",
        ],
    }

    result = await mireye_client.fetch(payload)
    mapped = map_mireye_response(result)

    fields = mapped["fields"]

    population = fields.get("county_population")

    if isinstance(population, dict):
        population = population.get("value")

    population_density = None

    if population is not None and radius_km > 0:
        area_km2 = 3.14159265359 * (radius_km ** 2)
        population_density = population / area_km2

    demand_estimate = {
        "population_within_catchment_proxy": population,
        "population_density_proxy_per_km2": population_density,
    }

    market_potential = {
        "catchment_radius_km": radius_km,
        "population_base": population,
    }

    return CatchmentData(
        address=address,
        lat=mapped["lat"],
        lng=mapped["lng"],
        radius_km=radius_km,
        population={
            "county_population": fields.get("county_population"),
            "county_population_density": fields.get(
                "county_population_density"
            ),
        },
        proximity={
            "nearest_major_road_distance_m": fields.get(
                "nearest_major_road_distance_m"
            ),
            "nearest_major_road_class": fields.get(
                "nearest_major_road_class"
            ),
        },
        data_quality=mapped.get("partial_failures", []),
        demand_estimate=demand_estimate,
        market_potential=market_potential,
    )