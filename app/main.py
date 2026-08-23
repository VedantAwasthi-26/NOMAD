# Load .env into the process environment before anything else runs --
# Vedant's Settings class (app/config/settings.py) reads .env on its own,
# but nothing else did, so GROQ_API_KEY never reached langchain-groq at
# runtime even when it was sitting right there in .env. Must happen before
# any app.* import below, since app.config.settings.Settings() is built
# at import time (via app.integrations.mireye.client) the moment the
# first route module is imported.
from dotenv import load_dotenv

load_dotenv()

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
from app.api.routes.catchment import router as catchment_router
from app.api.routes.reverse_logistics import router as reverse_logistics_router
from ai_engine.routes.decision import router as decision_router


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
app.include_router(catchment_router)
app.include_router(reverse_logistics_router)
app.include_router(decision_router)
