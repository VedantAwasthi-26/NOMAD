from fastapi import APIRouter
from pydantic import BaseModel

from app.integrations.mireye.permit_research import PermitResearchData
from app.services.permit_research_service import get_permit_research


router = APIRouter(
    prefix="/permit-research",
    tags=["Permit Research"],
)


class PermitResearchRequest(BaseModel):
    address: str
    business_type: str
    intended_use: str


@router.post("/", response_model=PermitResearchData)
async def permit_research(
    request: PermitResearchRequest,
):
    return await get_permit_research(
        request.address,
        request.business_type,
        request.intended_use,
    )