from typing import Any
from pydantic import BaseModel


class RiskData(BaseModel):
    lat: float
    lng: float
    facility_risks: dict[str, Any]
    route_risks: dict[str, Any]
    environmental_risks: dict[str, Any]
    data_quality: list[dict[str, Any]]