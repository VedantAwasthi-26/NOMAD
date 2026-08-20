from fastapi import FastAPI
from app.api.routes.locations import router as locations_router
from app.api.routes.verification import router as verification_router
from app.api.routes.feasibility import router as feasibility_router
from app.api.routes.regulatory import router as regulatory_router
from app.api.routes.site_selection import router as site_selection_router
from app.api.routes.risk import router as risk_router
from app.api.routes.multi_location import router as multi_location_router
from app.api.routes.permit_research import router as permit_research_router
from app.api.routes.decision_engine import router as decision_engine_router


app = FastAPI(
    title="NOMAD Backend",
    version="0.1.0"
)

app.include_router(locations_router)
app.include_router(verification_router)
app.include_router(feasibility_router)
app.include_router(regulatory_router)
app.include_router(site_selection_router)
app.include_router(risk_router)
app.include_router(multi_location_router)
app.include_router(permit_research_router)
app.include_router(decision_engine_router)
