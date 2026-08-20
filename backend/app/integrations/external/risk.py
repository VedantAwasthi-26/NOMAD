from typing import Any
from pydantic import BaseModel


class ExternalRiskData(BaseModel):
    weather_alerts: list[dict[str, Any]]
    disaster_alerts: list[dict[str, Any]]
    data_quality: list[dict[str, Any]]