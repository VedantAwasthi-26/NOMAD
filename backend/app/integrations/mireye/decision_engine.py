from typing import Any
from pydantic import BaseModel


class DecisionEngineData(BaseModel):
    address: str
    lat: float
    lng: float
    location_context: dict[str, Any]
    data_quality: list[dict[str, Any]]