#!/usr/bin/env python3
"""Tests for scripts/readme/markup/awesome.py – awesome-list rendering helpers."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.readme.markup.awesome import (  # noqa: E402
    format_resource_entry,
    generate_section_content,
    generate_toc,
    generate_weekly_section,
)


def make_resource(**overrides) -> dict:
    base = {
        "Display Name": "My Tool",
        "Primary Link": "https://example.com",
        "Author Name": "Alice",
        "Author Link": "https://github.com/alice",
        "Description": "A handy tool.",
        "Removed From Origin": "FALSE",
        "Category": "Tooling",
        "Sub-Category": "General",
        "Date Added": "2024-01-01",
    }
    base.update(overrides)
    return base


def make_category(name="Tooling", icon="🔧", subcats=None) -> dict:
    if subcats is None:
        subcats = [{"name": "General"}]
    return {
        "name": name,
        "icon": icon,
        "description": f"Description of {name}.",
        "subcategories": subcats,
    }


# ---------------------------------------------------------------------------
# format_resource_entry
# ---------------------------------------------------------------------------

class TestFormatResourceEntry:
    def test_basic_entry_with_link(self):
        result = format_resource_entry(make_resource())
        assert "- [My Tool](https://example.com)" in result
        assert "by [Alice](https://github.com/alice)" in result
        assert "A handy tool." in result

    def test_description_period_appended_when_missing(self):
        result = format_resource_entry(make_resource(**{"Description": "No period"}))
        assert "No period." in result

    def test_description_with_existing_punctuation_not_doubled(self):
        for punct in ["!", "?"]:
            result = format_resource_entry(make_resource(**{"Description": f"Ends{punct}"}))
            # The description itself should not have punct appended again
            assert f"Ends{punct}{punct}" not in result

    def test_no_link_renders_plain_name(self):
        result = format_resource_entry(make_resource(**{"Primary Link": ""}))
        assert "My Tool" in result
        assert "]()" not in result

    def test_no_author_link_renders_plain_name(self):
        result = format_resource_entry(make_resource(**{"Author Link": ""}))
        assert "by Alice" in result
        assert "by [Alice]" not in result

    def test_no_author_omits_by_line(self):
        result = format_resource_entry(make_resource(**{"Author Name": "", "Author Link": ""}))
        assert " by " not in result

    def test_removed_from_origin_appends_note(self):
        result = format_resource_entry(make_resource(**{"Removed From Origin": "TRUE"}))
        assert "Removed from origin" in result

    def test_entry_starts_with_dash(self):
        assert format_resource_entry(make_resource()).startswith("- ")

    def test_no_description_no_separator_dash(self):
        result = format_resource_entry(make_resource(**{"Description": ""}))
        assert " - " not in result


# ---------------------------------------------------------------------------
# generate_toc
# ---------------------------------------------------------------------------

class TestGenerateToc:
    def test_toc_contains_contents_header(self):
        assert "## Contents" in generate_toc([], [])

    def test_category_with_no_resources_omitted_when_subcats_present(self):
        cats = [make_category("Tooling", "🔧", [{"name": "General"}])]
        csv_data = [make_resource(**{"Category": "OTHER"})]
        result = generate_toc(cats, csv_data)
        assert "Tooling" not in result

    def test_category_with_resources_included(self):
        cats = [make_category("Tooling", "🔧", [{"name": "General"}])]
        csv_data = [make_resource(**{"Category": "Tooling", "Sub-Category": "General"})]
        assert "Tooling" in generate_toc(cats, csv_data)

    def test_subcategory_with_resources_included(self):
        cats = [make_category("Tooling", "🔧", [{"name": "General"}, {"name": "IDE"}])]
        csv_data = [
            make_resource(**{"Category": "Tooling", "Sub-Category": "General"}),
            make_resource(**{"Category": "Tooling", "Sub-Category": "IDE"}),
        ]
        result = generate_toc(cats, csv_data)
        assert "General" in result
        assert "IDE" in result

    def test_subcategory_without_resources_omitted(self):
        cats = [make_category("Tooling", "🔧", [{"name": "General"}, {"name": "IDE"}])]
        csv_data = [make_resource(**{"Category": "Tooling", "Sub-Category": "General"})]
        result = generate_toc(cats, csv_data)
        assert "General" in result
        assert "IDE" not in result

    def test_category_without_subcats_always_shown(self):
        cats = [{"name": "Hooks", "icon": "🪝", "description": "", "subcategories": []}]
        assert "Hooks" in generate_toc(cats, [])

    def test_anchor_format_for_category(self):
        cats = [{"name": "Agent Skills", "icon": "🤖", "description": "", "subcategories": []}]
        result = generate_toc(cats, [])
        assert "agent-skills" in result.lower()


# ---------------------------------------------------------------------------
# generate_weekly_section – 7-day cutoff & minimum-3 fallback
# ---------------------------------------------------------------------------

class TestGenerateWeeklySection:
    def _dated(self, days_ago: int) -> dict:
        date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        return make_resource(**{"Date Added": date, "Display Name": f"Resource {days_ago}d ago"})

    def test_resources_within_7_days_included(self):
        result = generate_weekly_section([self._dated(3), self._dated(10)])
        assert "Resource 3d ago" in result

    def test_resources_older_than_7_days_excluded_when_enough_recent(self):
        csv_data = [self._dated(1), self._dated(2), self._dated(3), self._dated(10)]
        assert "Resource 10d ago" not in generate_weekly_section(csv_data)

    def test_minimum_3_resources_shown_when_not_enough_recent(self):
        csv_data = [self._dated(2), self._dated(20), self._dated(30)]
        result = generate_weekly_section(csv_data)
        assert "Resource 2d ago" in result
        assert "Resource 20d ago" in result
        assert "Resource 30d ago" in result

    def test_sorted_by_date_descending(self):
        csv_data = [self._dated(3), self._dated(1), self._dated(2)]
        result = generate_weekly_section(csv_data)
        assert result.index("1d ago") < result.index("2d ago") < result.index("3d ago")

    def test_resources_without_date_ignored(self):
        csv_data = [make_resource(**{"Date Added": ""}), self._dated(2)]
        result = generate_weekly_section(csv_data)
        assert "Resource 2d ago" in result

    def test_section_header_present(self):
        assert "## Latest Additions" in generate_weekly_section([self._dated(1)])

    def test_empty_csv_returns_header_only(self):
        assert "## Latest Additions" in generate_weekly_section([])


# ---------------------------------------------------------------------------
# generate_section_content
# ---------------------------------------------------------------------------

class TestGenerateSectionContent:
    def test_section_header_rendered(self):
        cat = make_category("Tooling", "🔧")
        csv_data = [make_resource(**{"Category": "Tooling", "Sub-Category": "General"})]
        assert "## Tooling 🔧" in generate_section_content(cat, csv_data)

    def test_category_description_rendered(self):
        cat = make_category()
        cat["description"] = "A great category."
        csv_data = [make_resource(**{"Category": "Tooling", "Sub-Category": "General"})]
        assert "> A great category." in generate_section_content(cat, csv_data)

    def test_subcategory_header_rendered(self):
        cat = make_category("Tooling", "🔧", [{"name": "General"}, {"name": "IDE"}])
        csv_data = [make_resource(**{"Category": "Tooling", "Sub-Category": "IDE"})]
        assert "### IDE" in generate_section_content(cat, csv_data)

    def test_empty_subcategory_omitted(self):
        cat = make_category("Tooling", "🔧", [{"name": "General"}, {"name": "IDE"}])
        csv_data = [make_resource(**{"Category": "Tooling", "Sub-Category": "General"})]
        assert "### IDE" not in generate_section_content(cat, csv_data)

    def test_resources_rendered_in_section(self):
        cat = make_category("Tooling", "🔧")
        csv_data = [make_resource(**{"Category": "Tooling", "Sub-Category": "General",
                                     "Display Name": "Special Tool"})]
        assert "Special Tool" in generate_section_content(cat, csv_data)
