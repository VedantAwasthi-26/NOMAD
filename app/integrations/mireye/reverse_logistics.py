from typing import Any
from pydantic import BaseModel


class ReverseLogisticsData(BaseModel):
    origin_address: str
    destination_addresses: list[str]
    origins: list[dict[str, Any]]
    destinations: list[dict[str, Any]]
    route_factors: dict[str, Any]
    destination_ranking: list[dict[str, Any]]
    data_quality: list[dict[str, Any]]