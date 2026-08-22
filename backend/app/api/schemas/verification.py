from pydantic import BaseModel


class VerificationRequest(BaseModel):
    address: str

from typing import Any
from pydantic import BaseModel


class VerificationRequest(BaseModel):
    address: str


class VerificationResponse(BaseModel):
    lat: float
    lng: float
    fetched_at: str
    fields: dict[str, Any]
    partial_failures: list[dict[str, Any]] = []