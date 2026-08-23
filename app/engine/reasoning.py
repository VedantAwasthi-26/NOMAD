"""
The LLM layer: explanation + verifier, with a capped retry loop and a
fact-only fallback. This is the only place in the engine that calls an
LLM -- everything upstream (scoring.py) is deterministic.

Runs on Groq (via `langchain-groq`), not Anthropic -- `GROQ_API_KEY` is
what this needs, not `ANTHROPIC_API_KEY`.

Structured output uses Groq's JSON Schema strict mode
(response_format={"type": "json_schema", "json_schema": {..., "strict":
True}}), called directly rather than through LangChain's
with_structured_output(). Two other approaches were tried first and both
failed on real Groq traffic against openai/gpt-oss-120b:
- LangChain's default method="function_calling" -> `groq.BadRequestError:
  tool_use_failed`. Confirmed as a real, open compatibility gap between
  Groq's gpt-oss models and LangChain's tool-forcing strategy --see
  https://github.com/langchain-ai/langchain/issues/34155.
- Unstructured response_format={"type": "json_object"} (no schema) ->
  intermittent `groq.BadRequestError: json_validate_failed` with an empty
  failed_generation -- a known rough edge with these reasoning models
  under Groq's own community forum reports.
JSON Schema strict mode is the one mode Groq's docs explicitly guarantee
for this model family (openai/gpt-oss-20b and openai/gpt-oss-120b --
https://console.groq.com/docs/structured-outputs): constrained decoding
on Groq's side, not the model's own judgment, is what makes the output
match the schema. DEFAULT_MODEL below must stay one of those two models
for that guarantee to hold -- an env override to a different model (e.g.
a Qwen model) is not covered by it.
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
# Must be openai/gpt-oss-120b or openai/gpt-oss-20b -- the two models Groq
# guarantees JSON Schema strict-mode compliance for. Override via
# NOMAD_ENGINE_MODEL only to switch between those two; check
# https://console.groq.com/docs/structured-outputs before pointing this at
# anything else, since strict mode isn't guaranteed elsewhere.
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


# Groq's JSON Schema strict mode: "required" must list every property, and
# "additionalProperties": false is mandatory -- both are hard requirements
# of strict mode, not stylistic choices. See
# https://console.groq.com/docs/structured-outputs.
_EXPLANATION_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "explanation_output",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"explanation": {"type": "string"}},
            "required": ["explanation"],
            "additionalProperties": False,
        },
    },
}

_VERIFIER_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "verifier_verdict",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "grounded": {"type": "boolean"},
                "issues": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["grounded", "issues"],
            "additionalProperties": False,
        },
    },
}


def _invoke_json_schema(
    llm, messages: list[dict], schema: type[BaseModel], response_format: dict
) -> BaseModel:
    """Calls Groq's JSON Schema strict mode directly, bypassing LangChain's
    with_structured_output() entirely -- see the module docstring for why
    (both LangChain's forced tool-calling and unstructured json_object
    mode failed on real Groq traffic against this model). Any parse/
    validation failure raises and is caught by the caller's existing
    except block."""
    response = llm.bind(response_format=response_format).invoke(messages)
    data = json.loads(response.content)
    return schema.model_validate(data)


def generate_explanation(payload: dict) -> str:
    """One explanation attempt. Raises if the model can't be reached --
    callers should catch and fall back, not let this bubble to the user."""
    result = _invoke_json_schema(
        _get_llm(),
        [
            {"role": "system", "content": EXPLANATION_SYSTEM_PROMPT},
            {"role": "user", "content": build_explanation_user_prompt(payload)},
        ],
        ExplanationOutput,
        _EXPLANATION_RESPONSE_FORMAT,
    )
    return result.explanation


def verify_explanation(factor_breakdown: list[dict], explanation: str) -> VerifierVerdict:
    return _invoke_json_schema(
        _get_llm(temperature=0.0),
        [
            {"role": "system", "content": VERIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": build_verifier_user_prompt(factor_breakdown, explanation)},
        ],
        VerifierVerdict,
        _VERIFIER_RESPONSE_FORMAT,
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
