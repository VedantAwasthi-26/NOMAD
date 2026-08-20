from pydantic import BaseModel
from typing import Any


class LocationData(BaseModel):
    lat: float
    lng: float
    fetched_at: str
    fields: dict[str, Any]
    partial_failures: list[dict[str, Any]] = []