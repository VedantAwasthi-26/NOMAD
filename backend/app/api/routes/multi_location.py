from fastapi import APIRouter
from pydantic import BaseModel

from app.integrations.mireye.multi_location import MultiLocationData
from app.services.multi_location_service import get_multi_location_data


router = APIRouter(
    prefix="/multi-location",
    tags=["Multi-Location Operations"],
)


class MultiLocationRequest(BaseModel):
    addresses: list[str]


@router.post("/", response_model=MultiLocationData)
async def multi_location(
    request: MultiLocationRequest,
):
    return await get_multi_location_data(request.addresses)
    