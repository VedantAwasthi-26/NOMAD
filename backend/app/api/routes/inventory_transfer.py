from fastapi import APIRouter
from pydantic import BaseModel

from app.integrations.mireye.inventory_transfer import InventoryTransferData
from app.services.inventory_transfer_service import get_inventory_transfer_data


router = APIRouter(
    prefix="/inventory-transfer",
    tags=["Inventory Transfer"],
)


class InventoryTransferRequest(BaseModel):
    source_addresses: list[str]
    destination_addresses: list[str]


@router.post("/", response_model=InventoryTransferData)
async def inventory_transfer(
    request: InventoryTransferRequest,
):
    return await get_inventory_transfer_data(
        request.source_addresses,
        request.destination_addresses,
    )