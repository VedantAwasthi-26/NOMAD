from typing import Any
from pydantic import BaseModel


class InventoryLocation(BaseModel):
    address: str
    lat: float
    lng: float
    fields: dict[str, Any]
    data_quality: list[dict[str, Any]]


class InventoryTransferData(BaseModel):
    source_locations: list[InventoryLocation]
    destination_locations: list[InventoryLocation]
    transfer_factors: dict[str, Any]
    transfer_ranking: list[dict[str, Any]]
    data_quality: list[dict[str, Any]]