#!/usr/bin/env python3
"""Tests for scripts/ids/resource_id.py – stable resource ID generation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import scripts.ids.resource_id as resource_id_module  # noqa: E402
from scripts.ids.resource_id import generate_resource_id  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures – mock category_manager
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_category_manager(monkeypatch: pytest.MonkeyPatch):
    class FakeManager:
        def get_category_prefixes(self):
            return {
                "Tooling": "tool",
                "Hooks": "hook",
                "Slash-Commands": "slash",
            }

    monkeypatch.setattr(resource_id_module, "category_manager", FakeManager())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGenerateResourceId:
    def test_returns_string(self):
        result = generate_resource_id("My Tool", "https://example.com", "Tooling")
        assert isinstance(result, str)

    def test_format_is_prefix_dash_hash(self):
        result = generate_resource_id("My Tool", "https://example.com", "Tooling")
        parts = result.split("-")
        assert len(parts) == 2
        prefix, hash_part = parts
        assert prefix == "tool"
        assert len(hash_part) == 8

    def test_known_category_uses_correct_prefix(self):
        result = generate_resource_id("Hook Tool", "https://example.com", "Hooks")
        assert result.startswith("hook-")

    def test_unknown_category_uses_res_fallback(self):
        result = generate_resource_id("Tool", "https://example.com", "Unknown Category")
        assert result.startswith("res-")

    def test_deterministic_same_inputs_same_id(self):
        id1 = generate_resource_id("My Tool", "https://example.com", "Tooling")
        id2 = generate_resource_id("My Tool", "https://example.com", "Tooling")
        assert id1 == id2

    def test_different_names_produce_different_ids(self):
        id1 = generate_resource_id("Tool A", "https://example.com", "Tooling")
        id2 = generate_resource_id("Tool B", "https://example.com", "Tooling")
        assert id1 != id2

    def test_different_links_produce_different_ids(self):
        id1 = generate_resource_id("My Tool", "https://example.com/a", "Tooling")
        id2 = generate_resource_id("My Tool", "https://example.com/b", "Tooling")
        assert id1 != id2

    def test_different_categories_with_same_name_and_link_produce_different_prefixes(self):
        id1 = generate_resource_id("Tool", "https://example.com", "Tooling")
        id2 = generate_resource_id("Tool", "https://example.com", "Hooks")
        # Different prefix, so IDs must differ
        assert id1 != id2

    def test_hash_is_8_chars(self):
        result = generate_resource_id("My Tool", "https://example.com", "Tooling")
        hash_part = result.split("-", 1)[1]
        assert len(hash_part) == 8

    def test_hash_is_hexadecimal(self):
        result = generate_resource_id("My Tool", "https://example.com", "Tooling")
        hash_part = result.split("-", 1)[1]
        int(hash_part, 16)  # Raises ValueError if not valid hex

    def test_empty_display_name_does_not_crash(self):
        result = generate_resource_id("", "https://example.com", "Tooling")
        assert result.startswith("tool-")
        assert len(result) == 5 + 8  # "tool-" + 8 hex chars

    def test_empty_link_does_not_crash(self):
        result = generate_resource_id("My Tool", "", "Tooling")
        assert result.startswith("tool-")

    def test_empty_name_and_link_not_same_as_other_empty_combos(self):
        id1 = generate_resource_id("", "", "Tooling")
        id2 = generate_resource_id("A", "", "Tooling")
        assert id1 != id2

    def test_slash_commands_prefix(self):
        result = generate_resource_id("/my-cmd", "https://example.com", "Slash-Commands")
        assert result.startswith("slash-")
