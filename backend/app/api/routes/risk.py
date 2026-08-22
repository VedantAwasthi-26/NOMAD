from fastapi import APIRouter
from app.api.schemas.verification import VerificationRequest
from app.integrations.mireye.risk import RiskData
from app.services.risk_service import get_risk_data


router = APIRouter(
    prefix="/risk",
    tags=["Risk Monitoring"]
)


@router.post("/", response_model=RiskData)
async def get_risk(request: VerificationRequest):
    return await get_risk_data(request.address)