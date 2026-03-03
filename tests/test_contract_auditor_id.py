"""Validate that contract API response models include auditor_id."""

import pytest


def test_contract_response_includes_auditor_id():
    """ContractResponse schema must include auditor_id for API responses."""
    from views.contracts import ContractResponse

    assert "auditor_id" in ContractResponse.model_fields


def test_contract_list_item_includes_auditor_id():
    """ContractListItem schema must include auditor_id for list responses."""
    from views.contracts import ContractListItem

    assert "auditor_id" in ContractListItem.model_fields


def test_contract_response_serializes_auditor_id():
    """ContractResponse output includes auditor_id key (can be null)."""
    from views.contracts import ContractResponse

    response = ContractResponse(
        id="test-id",
        user_id="user-1",
        form_stage="project_id",
        r2=False,
        status="open",
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
        auditor_id="auditor-123",
    )
    data = response.model_dump()
    assert "auditor_id" in data
    assert data["auditor_id"] == "auditor-123"


def test_contract_response_serializes_auditor_id_null():
    """ContractResponse output includes auditor_id when null."""
    from views.contracts import ContractResponse

    response = ContractResponse(
        id="test-id",
        user_id="user-1",
        form_stage="project_id",
        r2=False,
        status="open",
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
        auditor_id=None,
    )
    data = response.model_dump()
    assert "auditor_id" in data
    assert data["auditor_id"] is None
