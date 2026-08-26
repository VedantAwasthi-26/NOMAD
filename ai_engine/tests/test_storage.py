"""
Tests for ai_engine/storage.py -- the persistence layer that makes
StartupContext an actual memory instead of a per-request shape. Each
test gets its own throwaway SQLite file (via the tmp_path fixture,
monkeypatched over storage._DB_PATH) so tests can't see each other's
data and don't touch the real ai_engine/memory.db used by the running
app.
"""

from __future__ import annotations

import pytest

from ai_engine import storage


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_DB_PATH", tmp_path / "test_memory.db")


def test_get_returns_none_for_unknown_startup():
    assert storage.get_startup_context("never-seen") is None


def test_save_then_get_round_trips():
    from ai_engine.schemas import StartupContext

    saved = storage.save_startup_context(
        StartupContext(
            startup_id="s1",
            business_type="cold-chain logistics",
            required_capabilities=["cold storage"],
        )
    )
    assert saved.last_updated is not None  # stamped on save

    fetched = storage.get_startup_context("s1")
    assert fetched is not None
    assert fetched.business_type == "cold-chain logistics"
    assert fetched.required_capabilities == ["cold storage"]


def test_merge_fills_in_gaps_without_erasing_earlier_fields():
    # First call: only business_type.
    storage.merge_and_save_startup_context({"startup_id": "s2", "business_type": "retail"})

    # Second call: only intended_use -- business_type must survive.
    merged = storage.merge_and_save_startup_context({"startup_id": "s2", "intended_use": "new storefront"})

    assert merged.business_type == "retail"
    assert merged.intended_use == "new storefront"


def test_merge_unions_required_capabilities_instead_of_replacing():
    storage.merge_and_save_startup_context({"startup_id": "s3", "required_capabilities": ["cold storage"]})
    merged = storage.merge_and_save_startup_context(
        {"startup_id": "s3", "required_capabilities": ["three-phase power"]}
    )

    assert set(merged.required_capabilities) == {"cold storage", "three-phase power"}


def test_merge_does_not_duplicate_a_capability_already_on_file():
    storage.merge_and_save_startup_context({"startup_id": "s4", "required_capabilities": ["cold storage"]})
    merged = storage.merge_and_save_startup_context(
        {"startup_id": "s4", "required_capabilities": ["cold storage"]}
    )

    assert merged.required_capabilities == ["cold storage"]


def test_merge_merges_confirmed_facts_key_by_key():
    storage.merge_and_save_startup_context({"startup_id": "s5", "confirmed_facts": {"annual_revenue": "2M"}})
    merged = storage.merge_and_save_startup_context(
        {"startup_id": "s5", "confirmed_facts": {"employee_count": "12"}}
    )

    assert merged.confirmed_facts == {"annual_revenue": "2M", "employee_count": "12"}


def test_merge_requires_a_startup_id():
    with pytest.raises(ValueError):
        storage.merge_and_save_startup_context({"business_type": "retail"})


def test_intake_agent_second_call_reduces_missing_fields():
    from ai_engine.agents.intake_agent import intake_startup_data

    _, missing_after_first = intake_startup_data({"startup_id": "s6", "business_type": "manufacturing"})
    assert {m.field for m in missing_after_first} == {"intended_use", "required_capabilities"}

    context, missing_after_second = intake_startup_data(
        {"startup_id": "s6", "intended_use": "new factory", "required_capabilities": ["rail access"]}
    )
    assert missing_after_second == []
    # business_type from the first call is still there -- not resent, not lost.
    assert context.business_type == "manufacturing"
