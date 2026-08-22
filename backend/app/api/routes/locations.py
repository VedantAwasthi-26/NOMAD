from fastapi import APIRouter
from app.models.location import Location
from app.services.location_service import process_location

router = APIRouter()


@router.get("/locations/health")
def health_check():
    return {"status": "ok"}


@router.post("/locations/test")
def test_location(location: Location):
    return process_location(location)