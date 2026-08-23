"""
The LLM layer: explanation + verifier, with a capped retry loop and a
fact-only fallback. This is the only place in the engine that calls an
LLM -- everything upstream (scoring.py) is deterministic.

Runs on Groq (via `langchain-groq`), not Anthropic -- `GROQ_API_KEY` is
what this needs, not `ANTHROPIC_API_KEY`. Structured output relies on
tool-calling, so DEFAULT_MODEL must be a Groq-hosted model that supports
tool use (the Llama 3.1/3.3 instruct models do; check Groq's current
model list -- https://console.groq.com/docs/models -- since which models
are available there changes over time).

Not executable in the sandbox this was authored in (no package registry
access there) -- written and reviewed against the current LangChain /
Groq tool-use API, but give it a real smoke test against a live key
before trusting it in the pipeline.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from app.engine.prompts import (
    EXPLANATION_SYSTEM_PROMPT,
    VERIFIER_SYSTEM_PROMPT,
    build_explanation_user_prompt,
    build_verifier_user_prompt,
)
from app.engine.schemas import Recommendation

MAX_VERIFIER_RETRIES = 3
# Groq-hosted, tool-use-capable default. Override via NOMAD_ENGINE_MODEL if
# Groq has since deprecated this one -- check https://console.groq.com/docs/models.
DEFAULT_MODEL = os.getenv("NOMAD_ENGINE_MODEL", "openai/gpt-oss-120b")


class ExplanationOutput(BaseModel):
    """Forced structured output for the explanation node -- this is what
    makes 'structured output, not free text' real rather than aspirational."""

    explanation: str = Field(..., description="3-5 sentence grounded explanation")


class VerifierVerdict(BaseModel):
    grounded: bool = Field(..., description="True only if every claim traces to the evidence")
    issues: list[str] = Field(
        default_factory=list,
        description="Specific unsupported claims found, empty if grounded=True",
    )


def _get_llm(temperature: float = 0.2):
    # Imported lazily so this module can be imported (and its pure-python
    # helpers reused/tested) even in environments without langchain-groq
    # installed. Reads GROQ_API_KEY from the environment automatically,
    # same pattern ChatAnthropic used for ANTHROPIC_API_KEY.
    from langchain_groq import ChatGroq

    return ChatGroq(model=DEFAULT_MODEL, temperature=temperature)


def _invoke_json_mode(llm, messages: list[dict], schema: type[BaseModel]) -> BaseModel:
    """Calls the LLM with Groq's plain JSON-object response format,
    bypassing LangChain's with_structured_output() entirely.

    Two different failure modes were observed on Groq going through that
    wrapper, on two structurally different models:
    - method="function_calling" (the default): `groq.BadRequestError:
      tool_use_failed` -- "model did not call a tool".
    - method="json_mode": `groq.BadRequestError: json_validate_failed` --
      "Failed to validate JSON" with an empty failed_generation. This
      smells like langchain-groq's json_mode routing through Groq's
      stricter structured-outputs (json_schema) validation rather than
      the plain json_object mode, which these particular models don't
      reliably satisfy.

    This does exactly what Groq's own docs describe for JSON mode:
    response_format={"type": "json_object"} (no schema attached, so
    nothing for Groq to reject the generation against) plus a prompt that
    says "json" and spells out the exact shape -- then a plain
    json.loads() + pydantic validate on our side. Any parse/validation
    failure raises and is caught by the caller's existing except block."""
    response = llm.bind(response_format={"type": "json_object"}).invoke(messages)
    data = json.loads(response.content)
    return schema.model_validate(data)


def generate_explanation(payload: dict) -> str:
    """One explanation attempt. Raises if the model can't be reached --
    callers should catch and fall back, not let this bubble to the user."""
    result = _invoke_json_mode(
        _get_llm(),
        [
            {"role": "system", "content": EXPLANATION_SYSTEM_PROMPT},
            {"role": "user", "content": build_explanation_user_prompt(payload)},
        ],
        ExplanationOutput,
    )
    return result.explanation


def verify_explanation(factor_breakdown: list[dict], explanation: str) -> VerifierVerdict:
    return _invoke_json_mode(
        _get_llm(temperature=0.0),
        [
            {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": build_verifier_user_prompt(factor_breakdown, explanation)},
        ],
        VerifierVerdict,
    )


def _fact_only_explanation(recommendation: Recommendation) -> str:
    """The fallback path when the retry cap is hit or the API is
    unavailable: no prose reasoning, just the facts, so the user still
    gets something checkable rather than a hard failure."""
    lines = [
        f"Overall score: {recommendation.overall_score}/100"
        + (" (feasible)" if recommendation.feasible else " (not feasible)" if recommendation.feasible is False else ""),
    ]
    for f in recommendation.factor_breakdown:
        note = f" -- {f.note}" if f.note else ""
        lines.append(f"- {f.factor}: {f.score}/100 (source: {f.source_system.value}){note}")
    if recommendation.flagged_gaps:
        lines.append(f"Data gaps: {', '.join(g.field for g in recommendation.flagged_gaps)}")
    return "\n".join(lines)


def explain_and_verify(recommendation: Recommendation) -> Recommendation:
    """The full Diagram-1 explanation -> verify -> retry loop. Mutates and
    returns the Recommendation with `explanation` and `verified_groundedness`
    filled in. Never raises -- on total failure it falls back to a
    fact-only explanation rather than blocking the response."""

    payload = {
        "address": recommendation.address,
        "overall_score": recommendation.overall_score,
        "feasible": recommendation.feasible,
        "hard_floor_triggered": recommendation.hard_floor_triggered,
        "factor_breakdown": [f.model_dump() for f in recommendation.factor_breakdown],
        "flagged_gaps": [g.model_dump() for g in recommendation.flagged_gaps],
    }
    factor_breakdown_dicts = payload["factor_breakdown"]

    try:
        explanation: Optional[str] = None
        for attempt in range(1, MAX_VERIFIER_RETRIES + 1):
            explanation = generate_explanation(payload)
            verdict = verify_explanation(factor_breakdown_dicts, explanation)
            if verdict.grounded:
                recommendation.explanation = explanation
                recommendation.verified_groundedness = True
                return recommendation
            # not grounded -- retry, feeding the issues back in
            payload["previous_attempt_issues"] = verdict.issues

        # retries exhausted without a grounded explanation
        logger.warning(
            "explain_and_verify: exhausted %d retries without a grounded explanation for %r",
            MAX_VERIFIER_RETRIES, recommendation.address,
        )
        recommendation.explanation = _fact_only_explanation(recommendation)
        recommendation.verified_groundedness = False
        recommendation.requires_human_review = True
        return recommendation

    except Exception:
        # API unreachable, key missing, model doesn't support tool calling,
        # etc. -- degrade gracefully rather than failing the whole request,
        # but log the real cause instead of swallowing it silently (this
        # used to be a blind spot: the fallback fired with no trace of why).
        logger.exception(
            "explain_and_verify: LLM call failed for %r, falling back to fact-only explanation",
            recommendation.address,
        )
        recommendation.explanation = _fact_only_explanation(recommendation)
        recommendation.verified_groundedness = False
        recommendation.requires_human_review = True
        return recommendation
