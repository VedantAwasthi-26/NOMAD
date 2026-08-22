from fastapi import APIRouter
from app.api.schemas.verification import VerificationRequest
from app.integrations.mireye.site_selection import SiteSelectionData
from app.services.site_selection_service import get_site_selection_data


router = APIRouter(
    prefix="/site-selection",
    tags=["Site Selection"]
)


@router.post("/", response_model=SiteSelectionData)
async def site_selection(request: VerificationRequest):
    return await get_site_selection_data(request.address)