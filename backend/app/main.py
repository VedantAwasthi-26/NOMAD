from fastapi import FastAPI
from app.api.routes.locations import router as locations_router
from app.api.routes.verification import router as verification_router
from app.api.routes.feasibility import router as feasibility_router
from app.api.routes.regulatory import router as regulatory_router

app = FastAPI(
    title="NOMAD Backend",
    version="0.1.0"
)

app.include_router(locations_router)
app.include_router(verification_router)
app.include_router(feasibility_router)
app.include_router(regulatory_router)