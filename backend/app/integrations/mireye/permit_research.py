from typing import Any
from pydantic import BaseModel


class PermitResearchData(BaseModel):
    lat: float
    lng: float
    zoning: dict[str, Any]
    permits: dict[str, Any]
    restrictions: dict[str, Any]
    application_guidance: dict[str, Any]
    data_quality: list[dict[str, Any]]