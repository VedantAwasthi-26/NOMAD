from fastapi import APIRouter
from app.api.schemas.verification import VerificationRequest
from app.integrations.mireye.feasibility import FeasibilityResult
from app.services.feasibility_service import get_feasibility


router = APIRouter(prefix="/feasibility", tags=["Feasibility"])


@router.post("/", response_model=FeasibilityResult)
async def check_feasibility(request: VerificationRequest):
    return await get_feasibility(request.address)