# NOMAD 

NOMAD is a physical-world decision-intelligence platform built on top of
Mireye's location data API. It answers the questions companies ask about
their physical footprint where to open a facility, whether a site is
feasible, whether an address is real, what regulatory exposure a location
carries, and how a multi-location network compares by resolving addresses
into a standardized, cited physical-world profile and running scoring/
decision logic on top of it.


##  Quick Start

### Prerequisites
- Python: 3.11 or higher, pip (backend, ai-engine)
- Node.js: 18.x or higher, npm (frontend)
- A Mireye API key and base URL

### Clone the repository
```bash
git clone <repository-url>
cd NOMAD
```

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        
pip install -r requirements.txt
cp .env.example .env             # fill in MIREYE_API_KEY and MIREYE_BASE_URL
uvicorn app.main:app --reload
```
API comes up at `http://127.0.0.1:8000`, docs at `http://127.0.0.1:8000/docs`.

### AI & Decision Engine
```bash
cd ai-engine
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Consumes standardized location data from the backend and exposes
scoring/ranking/recommendation logic back to it — see `ai-engine/README.md`
for its interface once that module is running.

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 📁 Project Architecture
```
NOMAD/
├── .github/
│   └── workflows/
│       ├── ci-backend.yml       # runs on backend/** changes
│       ├── ci-ai-engine.yml     # runs on ai-engine/** changes
│       ├── ci-frontend.yml      # runs on frontend/** changes
│       └── pr-checks.yml        
│
├── backend/                      # Backend & Mireye Integration
│   ├── app/
│   │   ├── main.py                # FastAPI app, routers mounted here
│   │   ├── api/routes/            # one router per capability module
│   │   ├── services/               # business logic per capability
│   │   ├── integrations/
│   │   │   ├── mireye/            # Mireye API client + per-module data models
│   │   │   └── external/          # non-Mireye data sources (risk, regulatory, catchment)
│   │   ├── ingestion/              # CSV/JSON input connectors + normalization
│   │   ├── models/                  # shared models (location, physical context, provenance)
│   │   ├── validation/
│   │   └── config/settings.py      # env-based settings (Mireye key, base URL)
│   ├── tests/                      # one test module per capability
│   ├── docs/mireye_coverage.md     # Mireye field/category/coverage reference
│   ├── requirements.txt
│   └── .env.example
│
├── ai-engine/                     # AI & Decision Engine
│   ├── src/
│   │   ├── scoring/                 # site-selection, feasibility, regulatory/hazard scoring
│   │   ├── reasoning/                # prompts + reasoning pipeline over location data
│   │   └── interfaces/               # the contract this module exposes to the backend
│   ├── tests/
│   ├── scripts/                     # e.g. sanity-checking recommendation output
│   └── requirements.txt
│
├── frontend/                      # Frontend & Product
│   ├── src/
│   │   ├── components/
│   │   ├── pages/                   # dashboard shell, location input, results, etc.
│   │   └── api/                      # client for calling backend endpoints
│   ├── tests/
│   └── package.json
│
├── docs/                          # shared architecture notes / decision records
├── .gitignore
└── README.md
```
## Backend Capability Endpoints

The backend currently exposes 12 capability routers, mapped to the
opportunity areas in the project plan:

| Endpoint prefix | Capability |
|---|---|
| `/locations` | location intake |
| `/verification` | Address & Facility Verification |
| `/feasibility` | Site & Facility Feasibility Screening |
| `/site-selection` | Facility & Site Selection scoring |
| `/regulatory` | Regulatory, Zoning & Hazard data |
| `/risk` | Facility & Route Risk |
| `/multi-location` | Multi-Location Operations Monitor |
| `/permit-research` | Location-Based Regulatory & Permitting Research |
| `/decision-engine` | Central vs. Local Decision Engine |
| `/catchment` | Catchment-Based Population & Demand |
| `/reverse-logistics` | Reverse Logistics & Returns Network Planner |
| `/inventory-transfer` | Multi-Location Inventory Transfer Planner |

Each has its own service layer, a Mireye integration wrapper, and an
integration test. `docs/mireye_coverage.md` documents the underlying Mireye
data categories, metadata fields, and known coverage gaps.


##  Contribution Guidelines

Each module is owned by one person and worked on in its own branch
namespace. `main` is protected — no direct pushes, PRs required, CI checks
must pass.

### 1. Create a Feature Branch
```bash
git checkout -b backend/<feature-name>      # e.g. backend/csv-connector
git checkout -b ai/<feature-name>           # e.g. ai/site-selection-scoring
git checkout -b frontend/<feature-name>     # e.g. frontend/dashboard-shell
```

### 2. Work Only Inside Your Module
Stay inside `backend/`, `ai-engine/`, or `frontend/` respectively — this
keeps diffs small, keeps CI fast (each module's workflow is path-filtered to
only run on its own folder), and avoids merge conflicts with the other two
modules.

- **Backend:** add a new capability as `app/api/routes/<name>.py` +
  `app/services/<name>_service.py` + `app/integrations/mireye/<name>.py`,
  then mount the router in `app/main.py` and add a test in `tests/`.
- **AI engine:** add scoring/reasoning logic under `src/scoring/` or
  `src/reasoning/`, expose it through `src/interfaces/`, and add a test.
- **Frontend:** add pages under `src/pages/`, shared UI under
  `src/components/`, and API calls through `src/api/`.

##  Local Testing & Quality Assurance

Before pushing your changes or opening a Pull Request, run the checks for
your module locally:

**Backend / AI engine:**
```bash
pytest -q
ruff check .
uvicorn app.main:app --reload    # backend only — verify it boots
```

**Frontend:**
```bash
npm run lint
npm test -- --watch=false
npm run build
```

##  Pull Request Rules

- Push your branch to remote: `git push origin backend/<feature-name>`.
- Open a Pull Request targeting `main`.
- Branch name and PR title must be tagged `[backend]`, `[ai]`, `[frontend]`,
  or `[chore]` — enforced by `pr-checks.yml`.
- Ensure all automated GitHub Actions CI checks pass for your module.
- Describe what the PR adds — for backend PRs, note which Mireye fields or
  endpoints are involved.
