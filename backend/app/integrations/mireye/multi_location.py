from typing import Any
from pydantic import BaseModel


class LocationProfile(BaseModel):
    address: str
    lat: float
    lng: float
    fields: dict[str, Any]
    data_quality: list[dict[str, Any]]


class MultiLocationData(BaseModel):
    locations: list[LocationProfile]
    comparative_metrics: dict[str, Any]
    outlier_alerts: list[dict[str, Any]]
    network_insights: dict[str, Any]