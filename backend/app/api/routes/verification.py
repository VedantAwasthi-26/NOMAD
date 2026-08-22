from fastapi import APIRouter
from app.api.schemas.verification import VerificationRequest
from app.services.verification_service import verify_address
from app.api.schemas.verification import VerificationRequest, VerificationResponse

router = APIRouter(prefix="/verification", tags=["Verification"])


@router.post("/", response_model=VerificationResponse)
async def verify_address_route(request: VerificationRequest):
    return await verify_address(request.address)