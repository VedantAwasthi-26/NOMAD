from fastapi import APIRouter
from pydantic import BaseModel

from app.integrations.mireye.reverse_logistics import ReverseLogisticsData
from app.services.reverse_logistics_service import get_reverse_logistics_data


router = APIRouter(
    prefix="/reverse-logistics",
    tags=["Reverse Logistics"],
)


class ReverseLogisticsRequest(BaseModel):
    origin_address: str
    destination_addresses: list[str]


@router.post("/", response_model=ReverseLogisticsData)
async def reverse_logistics(
    request: ReverseLogisticsRequest,
):
    return await get_reverse_logistics_data(
        request.origin_address,
        request.destination_addresses,
    )