# API Contract

This documents the **real** NOMAD backend + AI decision-engine contract
that `src/lib/api.js` is built against — not a hypothetical REST API.
It's transcribed directly from the backend's FastAPI routes
(`app/api/routes/*.py`) and Pydantic response models
(`app/integrations/mireye/*.py`, `app/engine/schemas.py`).

Until the backend and AI decision-engine folders are merged into this
repo, set `VITE_USE_MOCK_DATA=true` (the default) and every function in
`api.js` returns a mock object shaped exactly like the real response
below — no frontend code changes needed when you flip it off.

```
VITE_API_BASE_URL=http://localhost:8000   # no /api prefix
VITE_USE_MOCK_DATA=false
```

All requests are `POST` with a JSON body and return JSON. All
endpoints are **address-driven** — there is no "list of sites" endpoint;
the frontend supplies addresses (typed in, or saved to the watchlist)
and the backend resolves them via Mireye.

---

## Raw evidence endpoints (Vedant's backend)

Each returns a bucket of Mireye-derived fields for one address. Nothing
here is scored — see the `/decision/*` endpoints below for that.

| Endpoint | Request body | Response model |
|---|---|---|
| `POST /verification/` | `{ address }` | `{ lat, lng, fetched_at, fields, partial_failures }` |
| `POST /feasibility/` | `{ address }` | `{ lat, lng, feasible, score, factors, blockers, data_quality }` |
| `POST /site-selection/` | `{ address }` | `{ lat, lng, physical, geographic, regulatory, demographic, data_quality }` |
| `POST /risk/` | `{ address }` | `{ lat, lng, facility_risks, route_risks, environmental_risks, data_quality }` |
| `POST /regulatory/` | `{ address }` | `{ lat, lng, regulations, restrictions, environmental_constraints, data_quality }` |
| `POST /catchment/` | `{ address, radius_km }` | `{ address, lat, lng, radius_km, population, proximity, demand_estimate, market_potential, data_quality }` |
| `POST /permit-research/` | `{ address, business_type, intended_use }` | `{ lat, lng, zoning, permits, restrictions, application_guidance, data_quality }` |
| `POST /multi-location/` | `{ addresses: [] }` | `{ locations: [{address,lat,lng,fields,data_quality}], comparative_metrics, outlier_alerts, network_insights }` |
| `POST /reverse-logistics/` | `{ origin_address, destination_addresses: [] }` | `{ origin_address, destination_addresses, origins, destinations, route_factors, destination_ranking, data_quality }` |
| `POST /inventory-transfer/` | `{ source_addresses: [], destination_addresses: [] }` | `{ source_locations, destination_locations, transfer_factors, transfer_ranking, data_quality }` |
| `POST /decision-engine/` | `{ address }` | `{ address, lat, lng, location_context, data_quality }` — a raw location-context bucket, **not** the AI layer despite the name |
| `GET /locations/health` | — | `{ status: "ok" }` — connectivity check |

`data_quality` is a list of `{ field, status, source }`-shaped entries
(exact keys vary slightly per endpoint); `partial_failures` on
`/verification/` follows the same idea. The frontend surfaces both
verbatim on the Data Sources page rather than inventing a status.

## AI decision engine endpoints (additive, `/decision/*`)

These run the backend's raw evidence through the scoring + explanation
engine and return a `Recommendation` — the contract the dashboard should
prefer wherever it shows a verdict, score, or explanation.

| Endpoint | Request body | Notes |
|---|---|---|
| `POST /decision/feasibility` | `{ address }` | Single-pipeline graph, feasibility mode |
| `POST /decision/site-selection` | `{ address }` | Single-pipeline graph, site-selection mode |
| `POST /decision/site-selection/agents` | `{ address }` | **Flagship** — 5-agent + Supervisor fan-out (Site Selection, Regulatory, Risk, Demand). Prefer this over `/decision/site-selection` |
| `POST /decision/logistics` | `{ origin_address, destination_addresses: [] }` | Ranks destinations; returns `{ origin_address, ranking: [...] }` (no fixed `Recommendation` shape) |
| `POST /decision/query` | `{ query, address?, destination_addresses? }` | Supervisor routes free text to whichever agent(s) apply |

`Recommendation` shape (`app/engine/schemas.py`):

```json
{
  "address": "...",
  "lat": 0, "lng": 0,
  "feasible": true,
  "overall_score": 0,
  "confidence": 0,
  "factor_breakdown": [
    { "factor": "hazard_safety", "raw_value": 0, "score": 0, "weight": 0,
      "contribution": 0, "confidence": 0, "source_system": "mireye",
      "source_fields": [], "note": null }
  ],
  "strengths": [],
  "flagged_gaps": [{ "field": "", "reason": "", "source_system": "mireye" }],
  "hard_floor_triggered": false,
  "requires_human_review": false,
  "explanation": "...",
  "verified_groundedness": true,
  "mireye_field_count": 0,
  "mireye_coverage_note": null
}
```

---

## Adding a new endpoint

1. Add a function to `src/lib/api.js` — follow the existing pattern:
   a real `request(...)` call, guarded by an `if (USE_MOCK) return ...`
   branch returning a same-shaped object from the `mock` object at the
   bottom of that file.
2. Wire it into a page with `useAsync` from `src/lib/useApi.js`,
   keying its `deps` on whatever it depends on (usually `activeAddress`
   from `useAppState()` in `src/lib/store.jsx`).
3. Done — `VITE_USE_MOCK_DATA` controls mock vs. live per environment,
   no other code changes needed.
