from typing import Any
from pydantic import BaseModel


class RegulatoryResult(BaseModel):
    lat: float
    lng: float
    regulations: dict[str, Any]
    restrictions: dict[str, Any]
    environmental_constraints: dict[str, Any]
    data_quality: list[dict[str, Any]]