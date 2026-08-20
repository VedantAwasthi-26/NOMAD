from pydantic import BaseModel
from typing import Any


class FeasibilityResult(BaseModel):
    lat: float
    lng: float
    feasible: bool | None
    score: float | None
    factors: dict[str, Any]
    blockers: list[str]
    data_quality: list[dict[str, Any]]