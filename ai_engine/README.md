# ai_engine — AI / decision engine

Your part of NOMAD, built directly on top of Vedant's existing services. This
README says exactly what's real and tested versus what still needs a live
run on your machine.

## What's here

- `schemas.py` — the standardized evidence schema (`FactorScore`,
  `EvidenceBundle`) and the final `Recommendation` output contract.
- `scoring.py` — the deterministic rules engine: feasibility, site
  selection, hazard safety, accessibility, infrastructure, regulatory fit,
  population coverage, the hard-floor safety rule, and confidence derived
  from Mireye's own data-completeness signal.
- `prompts.py` — system prompts for the explanation node (only allowed to
  narrate scores already computed) and the verifier node (fact-checks the
  explanation against the evidence).
- `reasoning.py` — calls a Groq-hosted LLM via `langchain-groq` with forced
  structured output, runs the explain → verify → retry loop (capped at 3
  attempts), and falls back to a fact-only explanation if the API is
  unreachable or the cap is hit. Default model is `openai/gpt-oss-120b`
  (override with `NOMAD_ENGINE_MODEL`) — needs to be tool-use-capable since
  structured output relies on tool calling.
- `graph.py` — the original single-pipeline LangGraph wiring: ingest → hard
  constraints (short-circuits disqualified sites before any LLM cost) →
  score → explain+verify → output. Still used by `/decision/feasibility`
  and `/decision/site-selection`. No HITL checkpoint node in this graph yet.
- `tests/test_scoring.py` — 8 unit tests covering good/bad/borderline/
  incomplete-data fixtures, the hard-floor rule, and scoring determinism.
- `agents/` — the confirmed multi-agent architecture: 5 specialist agents
  plus a shared deterministic Foundational Data Service (Vedant's existing
  fetch services, not a separate agent):
  - `regulatory_agent.py` — Regulatory & Compliance (capabilities 3, 4, 9).
    Deterministic only, no LLM call — hands scored evidence upstream.
  - `risk_agent.py` — Risk & Monitoring (capabilities 6, 7). Combines Mireye
    hazard fields with the live Open-Meteo/FEMA feeds Vedant already wired
    up (`score_live_conditions`); also exposes `get_network_risk_comparison`
    for cross-location outlier detection.
  - `demand_agent.py` — Demand & Market (capability 10). Wraps catchment
    population/density into a scored factor.
  - `site_selection_agent.py` — **the flagship**. Fans out to the three
    specialists above in parallel (`asyncio.gather`), reweights the Risk
    agent's `hazard_safety` factor into Site Selection's own 5-factor
    weighting, applies the hard floor, and is the only agent in this set
    that runs the LLM explain → verify loop.
  - `logistics_agent.py` — Logistics & Network (capabilities 11, 12).
    Replaces Vedant's placeholder linear ranking formula
    (`100 - min(road/1000,30) - min(substation/1000,20)`, no hazard signal)
    with the same graded scorers used everywhere else, plus a per-destination
    hazard_safety read — a flood-prone destination can no longer outrank a
    safer one just because it's closer to a substation.
- `supervisor.py` — the hybrid router: a keyword-based fast path over the
  five agents above, with an LLM fallback (forced structured output) for
  questions the keyword table doesn't recognize. `route()` returns a
  `RouteDecision` (which agents, why, whether the LLM fallback fired) so
  routing accuracy can be evaluated separately from agent output quality.
  `dispatch()`/`handle_query()` fan out to the resolved agent(s) in parallel.

New route file: `ai_engine/routes/decision.py`, wired into `app/main.py`.
Two generations of endpoints, both live:
- `POST /decision/feasibility`, `POST /decision/site-selection` — the
  original single-pipeline `graph.py`. Kept as-is, fully tested.
- `POST /decision/site-selection/agents` — **the one to demo**: the real
  5-agent fan-out via `run_site_selection()`.
- `POST /decision/logistics` — the Logistics & Network agent's ranked
  destination list.
- `POST /decision/query` — the Supervisor: free-text question in, routed
  and dispatched to whichever agent(s) it resolves to.

## What's actually been verified vs. what needs a real run

This was built in a sandbox with **no PyPI access**, so `langchain`,
`langgraph`, `langchain-groq`, `fastapi`, and `pytest` could never be
installed here — only `pydantic`, `httpx`, `uvicorn`, and `pydantic_settings`
were available. Everything below was verified as thoroughly as that
constraint allows; here's the honest breakdown.

**Fully tested, passing, real:**
- `schemas.py` and `scoring.py` — all 8 tests in `tests/test_scoring.py`
  pass (`pytest ai_engine/tests/test_scoring.py -v` to confirm on your own
  machine).
- `agents/regulatory_agent.py`, `agents/risk_agent.py`,
  `agents/demand_agent.py`, `agents/site_selection_agent.py`,
  `agents/logistics_agent.py`, `supervisor.py` — every file `py_compile`
  clean, and each **run end-to-end against fixture data** (Vedant's real
  service functions monkeypatched with realistic return shapes, so this
  exercises the actual aggregation/fan-out/scoring code paths, not just
  imports):
  - `run_site_selection()` produced a real `Recommendation` (score 79.94,
    6 factors including the informational `live_conditions` read, correct
    Mireye field count and gap list) from a simulated three-agent fan-out.
  - `get_logistics_evidence()` correctly ranked a safe/close destination
    above one with a VE flood zone + seismic category F, and correctly
    tripped the hard floor on the unsafe one — something Vedant's original
    placeholder formula (road/substation distance only) could never catch.
  - `supervisor.handle_query()` correctly routed a two-concern question
    ("what regulations and hazard risks apply") to exactly `{regulatory,
    risk}` via the keyword fast path (no LLM call needed) and returned both
    agents' evidence from a real parallel `asyncio.gather` dispatch.
  - `rule_based_route()` was checked against 5 single-concern queries (one
    per agent) plus one deliberately unrecognized query, confirming the
    fast path resolves the obvious cases and correctly falls through
    (`None`) to the LLM router otherwise.
  The one thing *not* exercised here is the LLM calls themselves
  (`reasoning.generate_explanation`/`verify_explanation`, and
  `supervisor.llm_route`) — those need `langchain-groq` and a real
  `GROQ_API_KEY`, neither available in this sandbox. Their fallback
  paths (fact-only explanation, `requires_human_review=True`) *were*
  exercised, since that's what fires when the LLM call isn't reachable.
- `prompts.py`, `graph.py`, `ai_engine/routes/decision.py` — `py_compile`
  clean; `graph.py`'s node functions and routing logic are plain Python
  (no LLM inside `node_hard_constraints`/`route_after_constraints`) so
  their correctness doesn't depend on the untested LLM layer.

**Needs a real run before a demo:** anything that actually calls the LLM —
`reasoning.generate_explanation`, `reasoning.verify_explanation`,
`supervisor.llm_route` — plus the full FastAPI app (`fastapi` itself
couldn't be installed here, so the routes were verified by calling their
underlying functions directly, not through an actual HTTP request). Written
correctly against the current LangChain/Groq tool-use API, but **give
the `/decision/site-selection/agents` and `/decision/query` endpoints a
real smoke test against your own `GROQ_API_KEY` before trusting them
in a demo.** Also worth a quick check that whatever model `NOMAD_ENGINE_MODEL`
resolves to actually supports tool calling on Groq — not every model in
their catalog does, and `with_structured_output` depends on it.

## Setup on your machine

```bash
pip install -r requirements.txt
cp .env.example .env
# fill in GROQ_API_KEY (and MIREYE_API_KEY/MIREYE_BASE_URL if not already set)

# 1. Confirm the deterministic core still passes (should be instant, no API key needed)
pytest ai_engine/tests/test_scoring.py -v

# 2. Smoke-test the full pipeline against a real Mireye + Groq call
uvicorn app.main:app --reload
# then, in another terminal:
curl -X POST http://localhost:8000/decision/feasibility \
  -H "Content-Type: application/json" \
  -d '{"address": "1600 Pennsylvania Avenue NW, Washington, DC"}'

# 3. The multi-agent flagship -- this is the one to demo
curl -X POST http://localhost:8000/decision/site-selection/agents \
  -H "Content-Type: application/json" \
  -d '{"address": "1600 Pennsylvania Avenue NW, Washington, DC"}'

# 4. The Supervisor -- free-text question, routed and dispatched automatically
curl -X POST http://localhost:8000/decision/query \
  -H "Content-Type: application/json" \
  -d '{"query": "what regulations and hazard risks apply here?", "address": "1600 Pennsylvania Avenue NW, Washington, DC"}'
```

If step 2 errors, the most likely causes, in order: missing/invalid
`GROQ_API_KEY`, `NOMAD_ENGINE_MODEL` pointing at a Groq model that doesn't
support tool calling (structured output needs it — swap in a Llama
3.1/3.3 instruct model if unsure), a LangChain/LangGraph API surface that
shifted slightly from what's pinned in `requirements.txt` (check the error
against `langchain-groq`'s current `with_structured_output` signature), or
a Mireye field name mismatch if Vedant's schema has moved since this was
written.

## Known simplifications, worth revisiting

- **Regulatory scoring (`score_regulatory_fit`) uses simple penalty flags**,
  not a graded score — reasonable for a first pass, but worth tuning once
  you see real regulatory field values from `get_regulatory_data()`.
- **Normalization thresholds throughout `scoring.py`** (e.g. "5km = 0
  accessibility") are documented assumptions, not calibrated against real
  data. Revisit once you have a real set of known-good/known-bad addresses
  to check them against.
- **`decide_site_selection` doesn't yet call `get_catchment_data()`** for a
  richer population estimate — it currently reads `county_population` off
  `get_site_selection_data()`'s `demographic` bucket, which is present but
  coarser than the catchment-specific radius calculation Vedant's catchment
  service does. Wiring that in is a natural next step, not a blocker.
- **Confidence is currently based only on which fields resolved**, not on
  Mireye's per-field confidence/vintage metadata — because `map_mireye_response()`
  doesn't currently capture that metadata (see the earlier findings on
  Vedant's repo). If he adds it, `confidence_from_completeness` is the
  function to extend.
- **The Supervisor's LLM fallback (`llm_route`) hasn't been tested against
  a real model** — only the keyword fast path has real coverage. Worth a
  handful of deliberately ambiguous test queries once you have an API key,
  to see what it actually resolves to.
- **`regulatory_agent.py` assumes a shape for `permit.data_quality` entries**
  (`.get("field")` / `.get("reason")`) that hasn't been checked against a
  real Mireye response yet — if `get_permit_research()`'s data_quality list
  turns out to have a different shape, `get_regulatory_evidence` will still
  run (it defaults missing keys to `"unknown"`/a generic reason) but the gap
  descriptions won't be as specific as intended.
- **`logistics_agent.py` makes one extra `get_risk_data()` call per
  destination** (for the hazard_safety read) on top of Vedant's existing
  reverse-logistics fetch — fine for a demo-sized destination list, but if
  you ever compare dozens of destinations at once, that's dozens of extra
  Mireye calls fired in parallel via `asyncio.gather`; worth keeping an eye
  on rate limits if the destination list grows.
