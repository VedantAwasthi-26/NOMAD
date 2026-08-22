from typing import Any
from pydantic import BaseModel


class CatchmentData(BaseModel):
    address: str
    lat: float
    lng: float
    radius_km: float
    population: dict[str, Any]
    proximity: dict[str, Any]
    demand_estimate: dict[str, Any]
    market_potential: dict[str, Any]
    data_quality: list[dict[str, Any]]