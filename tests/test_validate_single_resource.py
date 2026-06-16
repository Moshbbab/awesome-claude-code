#!/usr/bin/env python3
"""Tests for single resource validation helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import scripts.validation.validate_single_resource as validate_single_resource  # noqa: E402


def test_validate_single_resource_missing_primary() -> None:
    ok, enriched, errors = validate_single_resource.validate_single_resource(primary_link="")
    assert ok is False
    assert "Primary link is required" in errors
    assert "active" not in enriched


def test_validate_single_resource_primary_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_validate(url: str):
        return False, 500, None, None

    monkeypatch.setattr(validate_single_resource, "validate_url", fake_validate)

    ok, enriched, errors = validate_single_resource.validate_single_resource(
        primary_link="https://example.com",
        display_name="Example",
        category="Test",
    )

    assert ok is False
    assert enriched["active"] == "FALSE"
    assert any("Primary URL validation failed" in err for err in errors)
    assert enriched["last_checked"]


def test_validate_single_resource_success_with_secondary(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_validate(url: str):
        calls.append(url)
        if len(calls) == 1:
            return True, 200, "MIT", "2024-06-01:00-00-00"
        return True, 200, None, None

    monkeypatch.setattr(validate_single_resource, "validate_url", fake_validate)

    ok, enriched, errors = validate_single_resource.validate_single_resource(
        primary_link="https://example.com",
        secondary_link="https://example.com/secondary",
        display_name="Example",
        category="Test",
    )

    assert ok is True
    assert errors == []
    assert enriched["license"] == "MIT"
    assert enriched["last_modified"] == "2024-06-01:00-00-00"
    assert enriched["active"] == "TRUE"
    assert enriched["last_checked"]
    assert calls == ["https://example.com", "https://example.com/secondary"]


def test_validate_resource_from_dict_maps_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_validate_single_resource(**_kwargs):
        return (
            True,
            {
                "license": "Apache-2.0",
                "last_modified": "2024-01-01:00-00-00",
                "last_checked": "2024-01-02:00-00-00",
            },
            [],
        )

    monkeypatch.setattr(
        validate_single_resource,
        "validate_single_resource",
        fake_validate_single_resource,
    )

    resource = {
        "primary_link": "https://example.com",
        "display_name": "Example",
        "category": "Test",
        "license": "NOT_FOUND",
    }

    ok, updated, errors = validate_single_resource.validate_resource_from_dict(resource)
    assert ok is True
    assert errors == []
    assert updated["license"] == "Apache-2.0"
    assert updated["last_modified"] == "2024-01-01:00-00-00"
    assert updated["last_checked"] == "2024-01-02:00-00-00"


# ---------------------------------------------------------------------------
# Edge cases – validate_single_resource
# ---------------------------------------------------------------------------

def test_validate_single_resource_no_secondary_link(monkeypatch: pytest.MonkeyPatch) -> None:
    """Secondary link is optional; omitting it should not cause errors."""
    def fake_validate(url: str):
        return True, 200, "MIT", "2024-01-01:00-00-00"

    monkeypatch.setattr(validate_single_resource, "validate_url", fake_validate)
    ok, enriched, errors = validate_single_resource.validate_single_resource(
        primary_link="https://example.com",
    )
    assert ok is True
    assert errors == []


def test_validate_single_resource_secondary_failure_makes_result_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failing secondary link causes the overall validation to fail."""
    calls: list[str] = []

    def fake_validate(url: str):
        calls.append(url)
        if "secondary" in url:
            return False, 404, None, None
        return True, 200, "MIT", "2024-01-01:00-00-00"

    monkeypatch.setattr(validate_single_resource, "validate_url", fake_validate)
    ok, enriched, errors = validate_single_resource.validate_single_resource(
        primary_link="https://example.com",
        secondary_link="https://example.com/secondary",
    )
    assert ok is False
    assert any("Secondary URL" in e for e in errors)
    assert len(calls) == 2  # Both primary and secondary were checked


def test_validate_single_resource_license_from_primary_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """License detected from primary link should appear in enriched data."""
    def fake_validate(url: str):
        return True, 200, "Apache-2.0", None

    monkeypatch.setattr(validate_single_resource, "validate_url", fake_validate)
    _, enriched, _ = validate_single_resource.validate_single_resource(
        primary_link="https://example.com",
        license="NOT_FOUND",
    )
    assert enriched.get("license") == "Apache-2.0"


def test_validate_single_resource_last_checked_always_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """last_checked should be a non-empty timestamp regardless of success/failure."""
    def fake_validate(url: str):
        return False, 500, None, None

    monkeypatch.setattr(validate_single_resource, "validate_url", fake_validate)
    _, enriched, _ = validate_single_resource.validate_single_resource(
        primary_link="https://example.com",
    )
    assert enriched.get("last_checked", "") != ""


# ---------------------------------------------------------------------------
# Edge cases – validate_resource_from_dict
# ---------------------------------------------------------------------------

def test_validate_resource_from_dict_missing_primary_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A resource dict missing primary_link should propagate the error."""
    def fake_validate_single_resource(**_kwargs):
        return False, {}, ["Primary link is required"]

    monkeypatch.setattr(
        validate_single_resource, "validate_single_resource", fake_validate_single_resource
    )
    ok, _, errors = validate_single_resource.validate_resource_from_dict({})
    assert ok is False
    assert errors != []


def test_validate_resource_from_dict_passes_all_known_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All recognised fields from the dict should be forwarded as kwargs."""
    received: dict = {}

    def fake_validate_single_resource(**kwargs):
        received.update(kwargs)
        return True, {}, []

    monkeypatch.setattr(
        validate_single_resource, "validate_single_resource", fake_validate_single_resource
    )
    resource = {
        "primary_link": "https://example.com",
        "secondary_link": "https://docs.example.com",
        "display_name": "Example",
        "category": "Tooling",
        "license": "MIT",
        "subcategory": "General",
        "author_name": "Alice",
        "author_link": "https://github.com/alice",
        "description": "A great tool.",
    }
    validate_single_resource.validate_resource_from_dict(resource)
    assert received.get("primary_link") == "https://example.com"
    assert received.get("display_name") == "Example"
