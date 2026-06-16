#!/usr/bin/env python3
"""Tests for scripts/readme/markup/visual.py – visual README rendering helpers."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.readme.markup.visual import (  # noqa: E402
    format_resource_entry,
    generate_toc_from_categories,
    generate_weekly_section,
)


def make_resource(**overrides) -> dict:
    base = {
        "Display Name": "My Tool",
        "Primary Link": "https://example.com",
        "Author Name": "Alice",
        "Description": "A handy tool.",
        "Removed From Origin": "FALSE",
        "Category": "Tooling",
        "Sub-Category": "General",
        "Date Added": "2024-01-01",
    }
    base.update(overrides)
    return base


def make_category(name="Tooling", cat_id="tooling", subcats=None) -> dict:
    if subcats is None:
        subcats = [{"name": "General", "id": "general"}]
    return {"name": name, "id": cat_id, "icon": "🔧",
            "description": f"Desc of {name}.", "subcategories": subcats}


# ---------------------------------------------------------------------------
# format_resource_entry – no assets_dir (avoids all file I/O)
# ---------------------------------------------------------------------------

class TestFormatResourceEntryNoAssets:
    def test_basic_backtick_link(self):
        result = format_resource_entry(make_resource(), assets_dir=None)
        assert "[`My Tool`](https://example.com)" in result

    def test_author_name_shown(self):
        assert "by Alice" in format_resource_entry(make_resource(), assets_dir=None)

    def test_no_author_omits_by(self):
        result = format_resource_entry(make_resource(**{"Author Name": ""}), assets_dir=None)
        assert " by " not in result

    def test_description_in_italics(self):
        assert "_A handy tool._" in format_resource_entry(make_resource(), assets_dir=None)

    def test_removed_from_origin_adds_note(self):
        row = make_resource(**{"Removed From Origin": "TRUE"})
        assert "Removed from origin" in format_resource_entry(row, assets_dir=None)

    def test_github_url_embeds_stats(self):
        row = make_resource(**{"Primary Link": "https://github.com/owner/repo"})
        assert "github-readme-stats" in format_resource_entry(row, assets_dir=None)

    def test_non_github_url_no_stats(self):
        row = make_resource(**{"Primary Link": "https://example.com"})
        assert "github-readme-stats" not in format_resource_entry(row, assets_dir=None)

    def test_removed_suppresses_github_stats(self):
        row = make_resource(**{
            "Primary Link": "https://github.com/owner/repo",
            "Removed From Origin": "TRUE",
        })
        assert "github-readme-stats" not in format_resource_entry(row, assets_dir=None)

    def test_no_description_no_italic_block(self):
        row = make_resource(**{"Description": ""})
        result = format_resource_entry(row, assets_dir=None)
        assert "_" not in result

    def test_separator_not_added_without_assets_dir(self):
        result = format_resource_entry(make_resource(), assets_dir=None, include_separator=False)
        assert "div align" not in result


# ---------------------------------------------------------------------------
# generate_toc_from_categories
# ---------------------------------------------------------------------------

class TestGenerateTocFromCategories:
    def test_returns_string(self):
        assert isinstance(generate_toc_from_categories(categories=[], csv_data=[]), str)

    def test_category_anchor_in_toc(self):
        cats = [make_category("Tooling", "tooling")]
        result = generate_toc_from_categories(categories=cats, csv_data=[])
        assert "tooling" in result.lower()

    def test_subcategory_with_resources_included(self):
        cats = [make_category("Tooling", "tooling")]
        csv_data = [make_resource(**{"Category": "Tooling", "Sub-Category": "General"})]
        result = generate_toc_from_categories(categories=cats, csv_data=csv_data)
        assert "general" in result.lower()

    def test_subcategory_without_resources_excluded(self):
        cats = [make_category("Tooling", "tooling", [
            {"name": "General", "id": "general"},
            {"name": "IDE", "id": "ide"},
        ])]
        csv_data = [make_resource(**{"Category": "Tooling", "Sub-Category": "General"})]
        result = generate_toc_from_categories(categories=cats, csv_data=csv_data)
        assert "toc-sub-ide" not in result

    def test_general_subcategory_uses_category_id_anchor(self):
        cats = [make_category("Tooling", "tooling")]
        csv_data = [make_resource(**{"Category": "Tooling", "Sub-Category": "General"})]
        result = generate_toc_from_categories(categories=cats, csv_data=csv_data)
        assert "tooling-general" in result

    def test_general_map_overrides_default_anchor(self):
        cats = [make_category("Tooling", "tooling")]
        csv_data = [make_resource(**{"Category": "Tooling", "Sub-Category": "General"})]
        general_map = {("tooling", "General"): "custom-anchor-xyz"}
        result = generate_toc_from_categories(
            categories=cats, csv_data=csv_data, general_map=general_map
        )
        assert "custom-anchor-xyz" in result

    def test_non_general_anchor_derived_from_name(self):
        cats = [make_category("Tooling", "tooling", [{"name": "IDE Integrations", "id": "ide"}])]
        csv_data = [make_resource(**{"Category": "Tooling", "Sub-Category": "IDE Integrations"})]
        result = generate_toc_from_categories(categories=cats, csv_data=csv_data)
        assert "ide-integrations" in result

    def test_no_csv_data_shows_all_subcats(self):
        cats = [make_category("Tooling", "tooling", [
            {"name": "General", "id": "general"},
            {"name": "IDE", "id": "ide"},
        ])]
        result = generate_toc_from_categories(categories=cats, csv_data=None)
        assert "general" in result.lower()

    def test_contains_div_wrapper(self):
        result = generate_toc_from_categories(categories=[], csv_data=[])
        assert "<div" in result and "</div>" in result


# ---------------------------------------------------------------------------
# generate_weekly_section
# ---------------------------------------------------------------------------

class TestVisualGenerateWeeklySection:
    def _dated(self, days_ago: int, name: str | None = None) -> dict:
        date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        return make_resource(**{"Date Added": date, "Display Name": name or f"Res{days_ago}d"})

    def test_includes_latest_additions_header_svg(self):
        assert "latest-additions-header" in generate_weekly_section([self._dated(1)])

    def test_recent_resources_included(self):
        assert "Res2d" in generate_weekly_section([self._dated(2)])

    def test_old_resources_excluded_when_enough_recent(self):
        csv_data = [self._dated(1, "A"), self._dated(2, "B"), self._dated(3, "C"),
                    self._dated(30, "Old")]
        assert "Old" not in generate_weekly_section(csv_data)

    def test_minimum_3_resources_shown(self):
        csv_data = [self._dated(1, "A"), self._dated(20, "B"), self._dated(40, "C")]
        result = generate_weekly_section(csv_data)
        assert "A" in result and "B" in result and "C" in result

    def test_resources_without_dates_skipped(self):
        csv_data = [
            make_resource(**{"Date Added": "", "Display Name": "Undated"}),
            self._dated(1, "Dated"),
        ]
        result = generate_weekly_section(csv_data)
        assert "Dated" in result
        assert "Undated" not in result
