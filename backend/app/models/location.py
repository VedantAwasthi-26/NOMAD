from pydantic import BaseModel
from typing import Optional

from app.models.physical_context import PhysicalContext
from app.models.provenance import Provenance


class Location(BaseModel):
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    physical_context: Optional[PhysicalContext] = None
    provenance: Optional[Provenance] = None