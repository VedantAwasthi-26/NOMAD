"""
Intake Agent -- the query-based agent for onboarding a startup's own data,
as distinct from every other agent in this package (which pull *location*
data from Mireye). This one checks the *business* data a startup submits
about itself (business type, intended use/model, required capabilities)
and, if something the engine actually needs is missing, generates a
specific request back to the user for just that field -- instead of
silently defaulting or letting a generic DataGap absorb it.

Design confirmed over a teammate WhatsApp thread: a startup submits its
initial data, the AI uses it to score things; separately, if a required
field wasn't in what was submitted, an agent should detect that specific
gap and ask for that specific field, rather than only flagging it after
the fact. This module is that detection step. It does not call an LLM --
"required field is missing" is a deterministic check, same spirit as
score_regulatory_fit()'s DataGap emission, so there's nothing here worth
spending a model call on.

Nothing here mutates or persists a StartupContext. It only ever produces:
- a StartupContext built from whatever was submitted (missing fields left
  None/empty, same as the model already allows), and
- zero or more StartupDataRequest objects, one per missing required field,
  for the caller (a route, eventually a frontend form) to act on.

This is the intake half of the Memory feature; MemoryUpdateProposal
(schemas.py) is the separate, later half -- updating a field that's
already on file, proposed by an agent, confirmed by a human. This module
never touches MemoryUpdateProposal: it only ever asks for a value that
isn't there yet.
"""

from __future__ import annotations

from ai_engine.schemas import StartupContext, StartupDataRequest

# The three data categories confirmed over the WhatsApp thread as what a
# startup submits up front: what kind of business it is, what it intends
# to use the site/recommendation for, and what it needs operationally.
# Each entry is (field name on StartupContext, human-readable prompt,
# reason shown alongside the prompt). Kept as a simple list rather than a
# dict so ordering is stable and predictable in the response.
REQUIRED_STARTUP_FIELDS: list[tuple[str, str, str]] = [
    (
        "business_type",
        "What type of business is this? (e.g. cold-chain logistics, retail, manufacturing)",
        "required to score regulatory fit and demand accurately for the right kind of business",
    ),
    (
        "intended_use",
        "What do you intend to use this site/recommendation for?",
        "required so permit research and the explanation layer can reason about the right use case",
    ),
    (
        "required_capabilities",
        "Does this business have any specific operational requirements? (e.g. cold storage, three-phase power, rail access)",
        "required to check candidate sites against what the business actually needs, not just generic scoring",
    ),
]


def _is_missing(context: StartupContext, field: str) -> bool:
    """A field counts as missing if it's None, an empty string, or an
    empty list -- covers every type REQUIRED_STARTUP_FIELDS currently
    uses (str or list[str]) without special-casing either."""
    value = getattr(context, field)
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, list) and not value:
        return True
    return False


def check_startup_context(context: StartupContext) -> list[StartupDataRequest]:
    """The core gap check: one StartupDataRequest per required field
    that's missing/empty on the given context, nothing more. Returns an
    empty list when everything required is present -- that's the signal
    to the caller that scoring can proceed without asking the user
    anything first."""
    return [
        StartupDataRequest(
            startup_id=context.startup_id,
            field=field,
            prompt=prompt,
            reason=reason,
        )
        for field, prompt, reason in REQUIRED_STARTUP_FIELDS
        if _is_missing(context, field)
    ]


def intake_startup_data(raw: dict) -> tuple[StartupContext, list[StartupDataRequest]]:
    """Entry point for a fresh intake submission: builds a StartupContext
    out of whatever the startup actually submitted (any field not present
    in `raw` just takes StartupContext's own default -- None/empty, same
    as today), then runs the completeness check against it.

    `raw` is expected to look like the body of an intake request --
    startup_id plus whichever of business_type / intended_use /
    required_capabilities / confirmed_facts / last_updated the startup
    provided. Unknown keys are ignored by StartupContext's own validation
    behavior (Pydantic's default extra="ignore"), so this doesn't need to
    pre-filter `raw` itself.

    Returns (context, missing) -- `missing` is empty exactly when nothing
    required was left out, which the caller can use to decide whether to
    go straight to scoring or to surface `missing` back to the user first."""
    context = StartupContext.model_validate(raw)
    missing = check_startup_context(context)
    return context, missing
