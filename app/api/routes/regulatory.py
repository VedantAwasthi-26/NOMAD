from fastapi import APIRouter
from app.api.schemas.verification import VerificationRequest
from app.integrations.mireye.regulatory import RegulatoryResult
from app.services.regulatory_service import get_regulatory_data


router = APIRouter(prefix="/regulatory", tags=["Regulatory"])


@router.post("/", response_model=RegulatoryResult)
async def get_regulatory(request: VerificationRequest):
    return await get_regulatory_data(request.address)