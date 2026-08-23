from typing import Any


async def get_market_benchmark(
    *,
    industry: str | None = None,
    geography: str | None = None,
) -> dict[str, Any]:
    return {
        "source": "public_market_benchmark",
        "industry": industry,
        "geography": geography,
        "penetration_rate": None,
        "demand_multiplier": None,
        "data_quality": [
            "external_market_benchmark_source_not_configured"
        ],
    }