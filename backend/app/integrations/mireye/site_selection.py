from typing import Any

from pydantic import BaseModel


class SiteSelectionData(BaseModel):
    lat: float
    lng: float
    physical: dict[str, Any]
    geographic: dict[str, Any]
    regulatory: dict[str, Any]
    demographic: dict[str, Any]
    logistics_proximity: list[dict[str, Any]]
    data_quality: list[dict[str, Any]]