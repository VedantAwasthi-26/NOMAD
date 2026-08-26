import sys
from pathlib import Path

# ai_engine/ lives as a flat sibling of backend/ at the repo root, outside
# backend/'s own working directory -- this app is run with backend/ as
# cwd (so `from app.api.routes.x import y` resolves against backend/app/),
# which means ai_engine isn't importable without an explicit sys.path
# entry pointing at the repo root. Two levels up from this file
# (backend/app/main.py -> backend/app -> backend -> repo root) is that root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv

load_dotenv()  # picks up GROQ_API_KEY (and anything else in .env) for ai_engine/reasoning.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
from app.api.routes.inventory_transfer import router as inventory_transfer_router
from ai_engine.routes.decision import router as decision_router

from ai_engine.routes.decision import router as decision_router

app = FastAPI(
    title="NOMAD Backend",
    version="0.1.0"
)

# Paarth's frontend (Vite dev server, default http://localhost:5173) is a
# different origin than this API (http://localhost:8000) -- without CORS
# enabled, every fetch() call from the browser gets silently blocked by
# the browser itself before it even reaches these routes. Wide open here
# since this is a hackathon demo, not a public deployment; tighten
# allow_origins to the real frontend URL before shipping this anywhere else.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(inventory_transfer_router)
app.include_router(decision_router)
