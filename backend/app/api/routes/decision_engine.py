from fastapi import APIRouter
from pydantic import BaseModel

from app.integrations.mireye.decision_engine import DecisionEngineData
from app.services.decision_engine_service import get_decision_engine_data


router = APIRouter(
    prefix="/decision-engine",
    tags=["Decision Engine"],
)


class DecisionEngineRequest(BaseModel):
    address: str


@router.post("/", response_model=DecisionEngineData)
async def decision_engine(
    request: DecisionEngineRequest,
):
    return await get_decision_engine_data(request.address)