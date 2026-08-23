"""
LangGraph wiring for the Feasibility / Site Selection decision flow --
Diagram 1 from the architecture docs, implemented: ingest -> hard
constraints -> score -> explain+verify -> output.

Requires `langgraph` (not installed in the sandbox this was authored in).
The node functions below are written against the current LangGraph
`StateGraph` API and call straight into scoring.py (already tested) and
reasoning.py -- give this a real run once you have the package installed
and an API key set, then check it against app/engine/tests/test_scoring.py's
fixtures for a first end-to-end smoke test.
"""

from __future__ import annotations

from typing import Any, Optional, TypedDict

from app.engine.schemas import Recommendation
from app.engine.scoring import (
    apply_hard_floor,
    confidence_from_completeness,
    find_feasibility_blockers,
    is_feasible,
    score_feasibility,
    score_site_selection,
)
from app.engine.reasoning import explain_and_verify


class EngineState(TypedDict, total=False):
    # inputs
    address: str
    lat: Optional[float]
    lng: Optional[float]
    mode: str  # "feasibility" | "site_selection"
    feasibility_fields: dict  # from Vedant's get_feasibility().factors
    site_selection_fields: dict  # from get_site_selection_data()
    regulatory_fields: dict  # from get_regulatory_data(), flattened

    # working state
    blockers: list[str]
    disqualified: bool
    recommendation: Recommendation


def node_hard_constraints(state: EngineState) -> EngineState:
    """Short-circuits obviously unsuitable locations before any scoring
    or LLM cost is spent on them."""
    fields = state.get("feasibility_fields") or state.get("site_selection_fields", {})
    blockers = find_feasibility_blockers(fields)
    return {**state, "blockers": blockers, "disqualified": bool(blockers)}


def node_score(state: EngineState) -> EngineState:
    """The deterministic core -- no LLM involved."""
    address = state["address"]
    lat, lng = state.get("lat"), state.get("lng")

    if state["mode"] == "feasibility":
        bundle = score_feasibility(address, state["feasibility_fields"], lat, lng)
        feasible = is_feasible(bundle)
    else:
        bundle = score_site_selection(
            address,
            state["site_selection_fields"],
            state.get("regulatory_fields", {}),
            lat,
            lng,
        )
        feasible = None

    capped_score, hard_floor_triggered = apply_hard_floor(bundle.factors, bundle.overall_score)
    confidence = confidence_from_completeness(bundle)

    strengths = [
        f.factor.replace("_", " ")
        for f in sorted(bundle.factors, key=lambda f: f.score, reverse=True)[:2]
        if f.score >= 70
    ]

    mireye_fields_used = sorted(
        {field for f in bundle.factors for field in f.source_fields}
    )

    recommendation = Recommendation(
        address=address,
        lat=lat,
        lng=lng,
        feasible=feasible,
        overall_score=capped_score,
        confidence=confidence,
        factor_breakdown=bundle.factors,
        strengths=strengths,
        flagged_gaps=bundle.gaps,
        hard_floor_triggered=hard_floor_triggered,
        requires_human_review=hard_floor_triggered or bool(state.get("blockers")),
        mireye_field_count=len(mireye_fields_used),
        mireye_coverage_note=f"Used {len(mireye_fields_used)} Mireye fields: {', '.join(mireye_fields_used)}",
    )
    return {**state, "recommendation": recommendation}


def node_disqualified_output(state: EngineState) -> EngineState:
    address = state["address"]
    recommendation = Recommendation(
        address=address,
        lat=state.get("lat"),
        lng=state.get("lng"),
        feasible=False,
        overall_score=0.0,
        confidence=1.0,
        factor_breakdown=[],
        flagged_gaps=[],
        hard_floor_triggered=True,
        requires_human_review=False,
        explanation="Disqualified before scoring: " + "; ".join(state["blockers"]),
        verified_groundedness=True,  # trivially true -- this text is generated from the blockers list directly, not by the LLM
    )
    return {**state, "recommendation": recommendation}


def node_explain(state: EngineState) -> EngineState:
    recommendation = explain_and_verify(state["recommendation"])
    return {**state, "recommendation": recommendation}


def route_after_constraints(state: EngineState) -> str:
    return "disqualified_output" if state.get("disqualified") else "score"


def build_graph():
    """Returns a compiled LangGraph app. Call with:

        app = build_graph()
        result = app.invoke({
            "address": "...", "mode": "feasibility",
            "feasibility_fields": {...},
        })
        recommendation = result["recommendation"]
    """
    from langgraph.graph import StateGraph, END

    graph = StateGraph(EngineState)

    graph.add_node("hard_constraints", node_hard_constraints)
    graph.add_node("score", node_score)
    graph.add_node("explain", node_explain)
    graph.add_node("disqualified_output", node_disqualified_output)

    graph.set_entry_point("hard_constraints")
    graph.add_conditional_edges(
        "hard_constraints",
        route_after_constraints,
        {"score": "score", "disqualified_output": "disqualified_output"},
    )
    graph.add_edge("score", "explain")
    graph.add_edge("explain", END)
    graph.add_edge("disqualified_output", END)

    return graph.compile()
