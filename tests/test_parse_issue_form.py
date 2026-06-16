#!/usr/bin/env python3
"""Tests for parse_issue_form.py – GitHub Issue body parsing and validation."""

from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import scripts.resources.parse_issue_form as parse_issue_form  # noqa: E402
from scripts.resources.parse_issue_form import (  # noqa: E402
    check_for_duplicates,
    parse_issue_body,
    validate_parsed_data,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_issue_body(**fields) -> str:
    """Build a minimal GitHub issue form body from keyword args."""
    defaults = {
        "Display Name": "My Tool",
        "Category": "Tooling",
        "Sub-Category": "General",
        "Primary Link": "https://example.com/tool",
        "Secondary Link": "_No response_",
        "Author Name": "Alice",
        "Author Link": "https://github.com/alice",
        "License": "MIT",
        "Other License": "",
        "Description": "A useful tool for Claude users.",
    }
    defaults.update(fields)
    sections = []
    for label, value in defaults.items():
        sections.append(f"### {label}\n\n{value}")
    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# parse_issue_body – section parsing
# ---------------------------------------------------------------------------

class TestParseIssueBody:
    def test_basic_fields_extracted(self):
        body = make_issue_body()
        data = parse_issue_body(body)
        assert data["display_name"] == "My Tool"
        assert data["category"] == "Tooling"
        assert data["subcategory"] == "General"
        assert data["primary_link"] == "https://example.com/tool"
        assert data["author_name"] == "Alice"
        assert data["author_link"] == "https://github.com/alice"
        assert data["license"] == "MIT"
        assert data["description"] == "A useful tool for Claude users."

    def test_no_response_secondary_link_is_empty(self):
        # "_No response_" lines are stripped, leaving an empty value
        body = make_issue_body(**{"Secondary Link": "_No response_"})
        data = parse_issue_body(body)
        # secondary_link may be absent or empty — either is acceptable
        assert data.get("secondary_link", "") == ""

    def test_explicit_secondary_link_captured(self):
        body = make_issue_body(**{"Secondary Link": "https://docs.example.com"})
        data = parse_issue_body(body)
        assert data["secondary_link"] == "https://docs.example.com"

    def test_none_subcategory_becomes_general(self):
        body = make_issue_body(**{"Sub-Category": "None / Not Applicable"})
        data = parse_issue_body(body)
        assert data["subcategory"] == "General"

    def test_empty_subcategory_becomes_general(self):
        body = make_issue_body(**{"Sub-Category": ""})
        data = parse_issue_body(body)
        assert data["subcategory"] == "General"

    def test_subcategory_prefix_stripped(self):
        body = make_issue_body(**{"Sub-Category": "Slash-Commands: Context Loading & Priming"})
        data = parse_issue_body(body)
        assert data["subcategory"] == "Context Loading & Priming"

    def test_other_license_overrides_license(self):
        body = make_issue_body(License="MIT", **{"Other License": "AGPL-3.0"})
        data = parse_issue_body(body)
        assert data["license"] == "AGPL-3.0"

    def test_empty_body_returns_empty_dict(self):
        data = parse_issue_body("")
        assert isinstance(data, dict)

    def test_body_with_extra_blank_lines(self):
        body = "### Display Name\n\n\n  My Tool  \n\n### Category\n\nTooling"
        data = parse_issue_body(body)
        assert data["display_name"] == "My Tool"
        assert data["category"] == "Tooling"


# ---------------------------------------------------------------------------
# parse_issue_body – Slash-Command normalisation
# ---------------------------------------------------------------------------

class TestSlashCommandNormalisation:
    def _parse(self, display_name: str) -> str:
        body = make_issue_body(**{"Display Name": display_name, "Category": "Slash-Commands"})
        return parse_issue_body(body)["display_name"]

    def test_slash_prepended_when_missing(self):
        assert self._parse("foo") == "/foo"

    def test_spaces_replaced_with_hyphens(self):
        assert self._parse("my command") == "/my-command"

    def test_result_is_lowercase(self):
        assert self._parse("FooBar") == "/foobar"

    def test_special_chars_removed(self):
        assert self._parse("/foo!bar@baz") == "/foobarbaz"

    def test_alphanumeric_underscore_colon_allowed(self):
        result = self._parse("foo_bar:baz")
        assert result == "/foo_bar:baz"

    def test_double_leading_slashes_collapsed(self):
        result = self._parse("//foo")
        assert result == "/foo"

    def test_triple_leading_slashes_collapsed(self):
        result = self._parse("///foo")
        assert result == "/foo"

    def test_original_display_name_tracked(self):
        body = make_issue_body(**{"Display Name": "MY TOOL", "Category": "Slash-Commands"})
        data = parse_issue_body(body)
        assert data["_original_display_name"] == "MY TOOL"
        assert data["display_name"] == "/my-tool"

    def test_non_slash_command_category_unchanged(self):
        body = make_issue_body(**{"Display Name": "My Tool", "Category": "Tooling"})
        data = parse_issue_body(body)
        assert data["display_name"] == "My Tool"


# ---------------------------------------------------------------------------
# validate_parsed_data – field & URL validation
# ---------------------------------------------------------------------------

class TestValidateParsedData:
    @pytest.fixture(autouse=True)
    def patch_categories(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            parse_issue_form.category_manager,
            "get_all_categories",
            lambda: ["Tooling", "Hooks", "Slash-Commands", "Workflows"],
        )

    def _valid_data(self, **overrides) -> dict:
        base = {
            "display_name": "My Tool",
            "category": "Tooling",
            "subcategory": "General",
            "primary_link": "https://example.com/tool",
            "author_name": "Alice",
            "author_link": "https://github.com/alice",
            "description": "A useful tool for Claude users.",
        }
        base.update(overrides)
        return base

    def test_valid_data_passes(self):
        ok, errors, _ = validate_parsed_data(self._valid_data())
        assert ok is True
        assert errors == []

    def test_missing_required_field_fails(self):
        data = self._valid_data()
        del data["display_name"]
        ok, errors, _ = validate_parsed_data(data)
        assert ok is False
        assert any("display_name" in e for e in errors)

    def test_all_required_fields_checked(self):
        required = ["display_name", "category", "primary_link", "author_name",
                     "author_link", "description"]
        for field in required:
            data = self._valid_data()
            del data[field]
            ok, errors, _ = validate_parsed_data(data)
            assert ok is False, f"Expected failure for missing field: {field}"

    def test_invalid_category_fails(self):
        ok, errors, _ = validate_parsed_data(self._valid_data(category="Made Up Category"))
        assert ok is False
        assert any("Invalid category" in e for e in errors)

    def test_primary_link_without_https_fails(self):
        ok, errors, _ = validate_parsed_data(self._valid_data(primary_link="http://example.com"))
        assert ok is False
        assert any("primary_link" in e for e in errors)

    def test_primary_link_with_spaces_fails(self):
        ok, errors, _ = validate_parsed_data(
            self._valid_data(primary_link="https://example .com")
        )
        assert ok is False
        assert any("primary_link" in e for e in errors)

    def test_description_too_short_fails(self):
        ok, errors, _ = validate_parsed_data(self._valid_data(description="Short"))
        assert ok is False
        assert any("too short" in e for e in errors)

    def test_description_exactly_min_length_passes(self):
        ok, errors, _ = validate_parsed_data(self._valid_data(description="x" * 10))
        assert ok is True
        assert errors == []

    def test_description_too_long_fails(self):
        ok, errors, _ = validate_parsed_data(self._valid_data(description="x" * 501))
        assert ok is False
        assert any("too long" in e for e in errors)

    def test_description_exactly_max_length_passes(self):
        ok, errors, _ = validate_parsed_data(self._valid_data(description="x" * 500))
        assert ok is True
        assert errors == []

    def test_no_license_string_replaced_with_not_found(self):
        data = self._valid_data(license="No License / Not Specified")
        ok, _, warnings = validate_parsed_data(data)
        assert ok is True
        assert data["license"] == "NOT_FOUND"
        assert any("No license" in w for w in warnings)

    def test_slash_command_with_multiple_slashes_fails(self):
        data = self._valid_data(
            display_name="/foo/bar",
            category="Slash-Commands",
        )
        ok, errors, _ = validate_parsed_data(data)
        assert ok is False
        assert any("multiple slashes" in e for e in errors)

    def test_slash_command_correction_generates_warning(self):
        data = self._valid_data(
            display_name="/foo",
            category="Slash-Commands",
            _original_display_name="foo",
        )
        _, _, warnings = validate_parsed_data(data)
        assert any("automatically corrected" in w for w in warnings)

    def test_test_display_name_generates_warning(self):
        _, _, warnings = validate_parsed_data(self._valid_data(display_name="test"))
        assert any("test entry" in w for w in warnings)


# ---------------------------------------------------------------------------
# check_for_duplicates
# ---------------------------------------------------------------------------

class TestCheckForDuplicates:
    @pytest.fixture
    def csv_with_existing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        csv_file = tmp_path / "THE_RESOURCES_TABLE.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Display Name", "Primary Link", "Category"]
            )
            writer.writeheader()
            writer.writerow({
                "Display Name": "Existing Tool",
                "Primary Link": "https://existing.com/tool",
                "Category": "Tooling",
            })
        monkeypatch.setattr(parse_issue_form, "REPO_ROOT", tmp_path)
        return csv_file

    def test_no_duplicate_returns_no_warnings(self, csv_with_existing):
        warnings = check_for_duplicates({
            "display_name": "New Tool",
            "primary_link": "https://new.com/tool",
        })
        assert warnings == []

    def test_duplicate_url_detected(self, csv_with_existing):
        warnings = check_for_duplicates({
            "display_name": "Something Else",
            "primary_link": "https://existing.com/tool",
        })
        assert len(warnings) == 1
        assert "already exists" in warnings[0]

    def test_duplicate_name_detected(self, csv_with_existing):
        warnings = check_for_duplicates({
            "display_name": "Existing Tool",
            "primary_link": "https://brand-new.com/tool",
        })
        assert len(warnings) == 1
        assert "same name" in warnings[0]

    def test_duplicate_check_is_case_insensitive(self, csv_with_existing):
        warnings = check_for_duplicates({
            "display_name": "EXISTING TOOL",
            "primary_link": "https://brand-new.com/tool",
        })
        assert len(warnings) == 1

    def test_missing_csv_returns_no_warnings(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(parse_issue_form, "REPO_ROOT", tmp_path)
        warnings = check_for_duplicates({"display_name": "Tool", "primary_link": "https://x.com"})
        assert warnings == []
