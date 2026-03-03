"""Validate get_auditor_schedule API response schema."""

import pytest


def test_auditor_schedule_response_has_items():
    """AuditorScheduleResponse must have items field."""
    from views.contracts import AuditorScheduleResponse

    assert "items" in AuditorScheduleResponse.model_fields


def test_auditor_schedule_entry_has_expected_fields():
    """AuditorScheduleEntry must have auditor_id, auditor_name, slots."""
    from views.contracts import AuditorScheduleEntry

    fields = set(AuditorScheduleEntry.model_fields)
    assert fields == {"auditor_id", "auditor_name", "slots"}


def test_auditor_schedule_slot_has_only_formatted_time_range():
    """AuditorScheduleSlot must have contract_id, formatted_time_range, zip, city (no date/start/end)."""
    from views.contracts import AuditorScheduleSlot

    fields = set(AuditorScheduleSlot.model_fields)
    assert fields == {"contract_id", "formatted_time_range", "zip", "city"}
    assert "date" not in fields
    assert "start_at_time" not in fields
    assert "end_at_time" not in fields


def test_auditor_schedule_response_serializes():
    """Full AuditorScheduleResponse serializes with expected shape."""
    from views.contracts import (
        AuditorScheduleResponse,
        AuditorScheduleEntry,
        AuditorScheduleSlot,
    )

    response = AuditorScheduleResponse(
        items=[
            AuditorScheduleEntry(
                auditor_id="auditor-1",
                auditor_name="Jane Auditor",
                slots=[
                    AuditorScheduleSlot(
                        contract_id="c1",
                        formatted_time_range="February 19, 2026 at 9:00 AM – 10:00 AM",
                        zip="01234",
                        city="Boston",
                    ),
                ],
            ),
        ],
    )
    data = response.model_dump()
    assert "items" in data
    assert len(data["items"]) == 1
    entry = data["items"][0]
    assert entry["auditor_id"] == "auditor-1"
    assert entry["auditor_name"] == "Jane Auditor"
    assert len(entry["slots"]) == 1
    slot = entry["slots"][0]
    assert slot["contract_id"] == "c1"
    assert slot["formatted_time_range"] == "February 19, 2026 at 9:00 AM – 10:00 AM"
    assert slot["zip"] == "01234"
    assert slot["city"] == "Boston"
    assert "date" not in slot
    assert "start_at_time" not in slot
    assert "end_at_time" not in slot


def test_auditor_schedule_slot_accepts_none_optional_fields():
    """AuditorScheduleSlot allows null for formatted_time_range, zip, city."""
    from views.contracts import AuditorScheduleSlot

    slot = AuditorScheduleSlot(
        contract_id="c1",
        formatted_time_range=None,
        zip=None,
        city=None,
    )
    data = slot.model_dump()
    assert data["contract_id"] == "c1"
    assert data["formatted_time_range"] is None
    assert data["zip"] is None
    assert data["city"] is None
