from pydantic import BaseModel
from typing import Optional


class Provenance(BaseModel):
    source: str
    retrieved_at: Optional[str] = None