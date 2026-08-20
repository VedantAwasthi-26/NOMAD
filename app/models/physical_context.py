from pydantic import BaseModel
from typing import Optional


class PhysicalContext(BaseModel):
    demographics: Optional[dict] = None
    zoning: Optional[dict] = None
    hazards: Optional[dict] = None
    accessibility: Optional[dict] = None
    proximity: Optional[dict] = None