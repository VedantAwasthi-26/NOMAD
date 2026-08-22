from fastapi import APIRouter
from pydantic import BaseModel

from app.integrations.mireye.catchment import CatchmentData
from app.services.catchment_service import get_catchment_data


router = APIRouter(
    prefix="/catchment",
    tags=["Catchment & Demand"],
)


class CatchmentRequest(BaseModel):
    address: str
    radius_km: float


@router.post("/", response_model=CatchmentData)
async def catchment(
    request: CatchmentRequest,
):
    return await get_catchment_data(
        request.address,
        request.radius_km,
    )