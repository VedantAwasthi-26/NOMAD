"""
Persistence for StartupContext -- the actual "memory" behind the Memory
feature. Until now, StartupContext and MemoryUpdateProposal (schemas.py)
and the intake agent (agents/intake_agent.py) were purely per-request
shapes: nothing kept a startup's confirmed facts around between calls, so
a caller had to resend the whole profile every single time, and a second
intake submission for the same startup would just overwrite whatever was
confirmed before. This module is the missing piece: a small SQLite-backed
store, keyed by startup_id, that the intake agent reads from and writes
to -- so a startup's confirmed information actually persists and
accumulates across multiple calls instead of living only inside one
request.

SQLite (Python's stdlib sqlite3, no new dependency) rather than a real
database server -- this is a hackathon project, not a production
deployment, and a single local file is the right amount of infrastructure
to prove memory is real without adding an external database to run and
configure. The file lives at ai_engine/memory.db, next to this module
(not wherever the process happens to have cwd set to), and is gitignored
-- it's runtime data, not something that belongs in version control.

Deliberately narrow: this module only persists StartupContext. It does
NOT apply a MemoryUpdateProposal automatically -- that schema exists
specifically so an AI-proposed change stays "pending" until a human
confirms it (see its docstring in schemas.py). Wiring a confirmed
MemoryUpdateProposal through to an actual write here is a separate, later
step this module intentionally doesn't take on its own.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ai_engine.schemas import StartupContext

_DB_PATH = Path(__file__).resolve().parent / "memory.db"


def _get_connection() -> sqlite3.Connection:
    """A fresh connection per call rather than one long-lived connection
    -- sqlite3 connections aren't safe to share across threads, and
    FastAPI can run sync code (which this is) in different worker
    threads per request. The table-creation is cheap and idempotent, so
    doing it here on every connection keeps this module usable without a
    separate init/startup step to remember to call."""
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS startup_context (
            startup_id TEXT PRIMARY KEY,
            business_type TEXT,
            intended_use TEXT,
            required_capabilities TEXT NOT NULL DEFAULT '[]',
            confirmed_facts TEXT NOT NULL DEFAULT '{}',
            last_updated TEXT
        )
        """
    )
    return conn


def get_startup_context(startup_id: str) -> Optional[StartupContext]:
    """Whatever's on file for this startup, or None if nothing's ever
    been saved for this startup_id -- a brand-new startup, same as
    today's behavior when no context is supplied at all."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT startup_id, business_type, intended_use, required_capabilities, "
            "confirmed_facts, last_updated FROM startup_context WHERE startup_id = ?",
            (startup_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    return StartupContext(
        startup_id=row[0],
        business_type=row[1],
        intended_use=row[2],
        required_capabilities=json.loads(row[3]),
        confirmed_facts=json.loads(row[4]),
        last_updated=row[5],
    )


def save_startup_context(context: StartupContext) -> StartupContext:
    """Upsert -- overwrites whatever was on file for this startup_id with
    exactly what's in `context`, stamping last_updated on the way in.
    Callers that want to fill in gaps rather than overwrite already-
    confirmed facts should go through merge_and_save_startup_context()
    below instead of calling this directly with a partial context."""
    context.last_updated = datetime.now(timezone.utc).isoformat()
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO startup_context
                (startup_id, business_type, intended_use, required_capabilities, confirmed_facts, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(startup_id) DO UPDATE SET
                business_type = excluded.business_type,
                intended_use = excluded.intended_use,
                required_capabilities = excluded.required_capabilities,
                confirmed_facts = excluded.confirmed_facts,
                last_updated = excluded.last_updated
            """,
            (
                context.startup_id,
                context.business_type,
                context.intended_use,
                json.dumps(context.required_capabilities),
                json.dumps(context.confirmed_facts),
                context.last_updated,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return context


def _first_non_empty(new_value: Any, old_value: Any) -> Any:
    if new_value is None:
        return old_value
    if isinstance(new_value, str) and not new_value.strip():
        return old_value
    return new_value


def merge_and_save_startup_context(raw: dict[str, Any]) -> StartupContext:
    """The actual "memory" behavior, and the reason this module exists:
    this is what makes a second intake call for the same startup_id fill
    in gaps rather than wiping out everything already confirmed.

    Whatever's already on file for this startup_id is the starting
    point. Only fields *present and non-empty* in `raw` override it --
    submitting {"startup_id": "s1", "intended_use": "warehouse"} for a
    startup that already has a confirmed business_type on file leaves
    that business_type untouched. required_capabilities is unioned
    rather than replaced (confirmed needs accumulate across calls, they
    don't get forgotten when a later call only mentions one new one),
    and confirmed_facts is merged key-by-key. A startup_id seen for the
    first time just becomes whatever was submitted, identical to
    StartupContext's own validation/defaults today.
    """
    startup_id = raw.get("startup_id")
    if not startup_id:
        raise ValueError("merge_and_save_startup_context requires a non-empty startup_id")

    existing = get_startup_context(startup_id)

    if existing is None:
        merged = StartupContext.model_validate(raw)
    else:
        merged_capabilities = list(existing.required_capabilities)
        for cap in raw.get("required_capabilities") or []:
            if cap not in merged_capabilities:
                merged_capabilities.append(cap)

        merged_facts = dict(existing.confirmed_facts)
        merged_facts.update(raw.get("confirmed_facts") or {})

        merged = StartupContext(
            startup_id=startup_id,
            business_type=_first_non_empty(raw.get("business_type"), existing.business_type),
            intended_use=_first_non_empty(raw.get("intended_use"), existing.intended_use),
            required_capabilities=merged_capabilities,
            confirmed_facts=merged_facts,
        )

    return save_startup_context(merged)
