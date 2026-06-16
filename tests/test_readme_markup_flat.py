#!/usr/bin/env python3
"""Tests for scripts/readme/markup/flat.py – flat-list README rendering helpers."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.readme.markup.flat import (  # noqa: E402
    generate_category_navigation,
    generate_navigation,
    generate_resources_table,
    generate_shields_badges,
    generate_sort_navigation,
)

SORT_TYPES = {
    "stars": ("Stars", "#FFD700", "by star count"),
    "date": ("Date", "#00BFFF", "by date added"),
    "releases": ("Releases", "#7CFC00", "by releases"),
}
CATEGORIES = {
    "all": ("all", "All", "#888888"),
    "tooling": ("tooling", "Tooling", "#4682B4"),
    "hooks": ("hooks", "Hooks", "#FF6347"),
}


def make_row(**overrides) -> dict:
    base = {
        "Display Name": "Test Tool",
        "Primary Link": "https://github.com/owner/repo",
        "Author Name": "Author",
        "Author Link": "https://github.com/author",
        "Category": "Tooling",
        "Sub-Category": "General",
        "Description": "A test tool.",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# generate_shields_badges
# ---------------------------------------------------------------------------

class TestGenerateShieldsBadges:
    def test_returns_img_tags(self):
        assert "img src=" in generate_shields_badges("owner", "repo")

    def test_shields_io_in_url(self):
        assert "shields.io" in generate_shields_badges("owner", "repo")

    def test_owner_and_repo_in_url(self):
        assert "myowner/myrepo" in generate_shields_badges("myowner", "myrepo")

    def test_flat_square_style_applied(self):
        assert "flat-square" in generate_shields_badges("owner", "repo")

    def test_badge_types_present(self):
        result = generate_shields_badges("owner", "repo")
        for badge in ["stars", "forks", "issues", "last-commit", "license"]:
            assert badge in result


# ---------------------------------------------------------------------------
# generate_sort_navigation
# ---------------------------------------------------------------------------

class TestGenerateSortNavigation:
    def test_all_sort_options_present(self):
        result = generate_sort_navigation("all", "stars", SORT_TYPES)
        for label in ["Stars", "Date", "Releases"]:
            assert label in result

    def test_selected_sort_has_border(self):
        result = generate_sort_navigation("all", "stars", SORT_TYPES)
        assert "border" in result

    def test_only_selected_sort_has_border_style(self):
        # The selected sort uses inline style="border: ..."; unselected ones don't
        result = generate_sort_navigation("all", "stars", SORT_TYPES)
        # Each selected item has one style="" attribute; count those
        assert result.count(' style="border') == 1

    def test_correct_filenames_in_links(self):
        result = generate_sort_navigation("tooling", "date", SORT_TYPES)
        assert "README_FLAT_TOOLING_STARS.md" in result
        assert "README_FLAT_TOOLING_DATE.md" in result

    def test_wrapped_in_p_tag(self):
        result = generate_sort_navigation("all", "stars", SORT_TYPES)
        assert result.startswith('<p align="center">')
        assert result.endswith("</p>")


# ---------------------------------------------------------------------------
# generate_category_navigation
# ---------------------------------------------------------------------------

class TestGenerateCategoryNavigation:
    def test_all_categories_present(self):
        result = generate_category_navigation("all", "stars", CATEGORIES)
        for label in ["All", "Tooling", "Hooks"]:
            assert label in result

    def test_selected_category_has_border_style(self):
        result = generate_category_navigation("tooling", "stars", CATEGORIES)
        assert result.count(' style="border') == 1

    def test_correct_filenames_in_links(self):
        result = generate_category_navigation("all", "stars", CATEGORIES)
        assert "README_FLAT_TOOLING_STARS.md" in result
        assert "README_FLAT_HOOKS_STARS.md" in result


# ---------------------------------------------------------------------------
# generate_resources_table
# ---------------------------------------------------------------------------

class TestGenerateResourcesTable:
    def test_empty_non_releases_message(self):
        assert "No resources found" in generate_resources_table([], "stars")

    def test_empty_releases_message(self):
        assert "No releases" in generate_resources_table([], "releases")

    def test_table_tags_present(self):
        result = generate_resources_table([make_row()], "stars")
        assert "<table>" in result and "</table>" in result

    def test_default_sort_has_4_columns(self):
        result = generate_resources_table([make_row()], "stars")
        assert "<th>Resource</th>" in result
        assert "<th>Category</th>" in result
        assert "<th>Sub-Category</th>" in result
        assert "<th>Description</th>" in result
        assert "<th>Version</th>" not in result

    def test_releases_sort_has_5_columns(self):
        result = generate_resources_table([make_row()], "releases")
        assert "<th>Version</th>" in result
        assert "<th>Release Date</th>" in result
        assert "<th>Category</th>" not in result

    def test_github_link_generates_shields(self):
        assert "shields.io" in generate_resources_table([make_row()], "stars")

    def test_non_github_link_no_shields(self):
        row = make_row(**{"Primary Link": "https://example.com/tool"})
        assert "shields.io" not in generate_resources_table([row], "stars")

    def test_resource_name_linked(self):
        result = generate_resources_table([make_row()], "stars")
        assert '<a href="https://github.com/owner/repo"><b>Test Tool</b></a>' in result

    def test_resource_without_link_shows_bold_name_not_hyperlinked(self):
        row = make_row(**{"Primary Link": "", "Author Name": "", "Author Link": ""})
        result = generate_resources_table([row], "stars")
        assert "<b>Test Tool</b>" in result
        # No anchor tag for the resource name itself
        assert '<a href=""><b>' not in result

    def test_releases_source_display_mapping(self):
        row = make_row(**{
            "Release Source": "github-releases",
            "Release Version": "v1.0",
            "Latest Release": "2024-01-15T00:00:00Z",
        })
        assert "GitHub" in generate_resources_table([row], "releases")

    def test_releases_unknown_source_shown_as_is(self):
        row = make_row(**{
            "Release Source": "custom-source",
            "Release Version": "v1.0",
            "Latest Release": "2024-01-15T00:00:00Z",
        })
        assert "custom-source" in generate_resources_table([row], "releases")

    def test_colspan_4_for_default_sort(self):
        assert 'colspan="4"' in generate_resources_table([make_row()], "stars")

    def test_colspan_5_for_releases_sort(self):
        row = make_row(**{
            "Release Source": "github-releases",
            "Release Version": "v1.0",
            "Latest Release": "2024-01-15T00:00:00Z",
        })
        assert 'colspan="5"' in generate_resources_table([row], "releases")

    def test_release_date_truncated_to_10_chars(self):
        row = make_row(**{
            "Release Source": "npm",
            "Release Version": "1.2.3",
            "Latest Release": "2024-06-15T12:34:56Z",
        })
        result = generate_resources_table([row], "releases")
        assert "2024-06-15" in result
        assert "12:34:56" not in result

    def test_no_author_omits_by_line(self):
        row = make_row(**{"Author Name": "", "Author Link": ""})
        assert "by" not in generate_resources_table([row], "stars")


# ---------------------------------------------------------------------------
# generate_navigation
# ---------------------------------------------------------------------------

class TestGenerateNavigation:
    def test_combined_output_includes_both_sections(self):
        result = generate_navigation("all", "stars", CATEGORIES, SORT_TYPES)
        assert "Stars" in result
        assert "All" in result

    def test_currently_viewing_label_present(self):
        assert "Currently viewing" in generate_navigation("all", "stars", CATEGORIES, SORT_TYPES)

    def test_releases_sort_appends_30_days_note(self):
        assert "past 30 days" in generate_navigation("all", "releases", CATEGORIES, SORT_TYPES)

    def test_non_releases_sort_no_30_days_note(self):
        assert "past 30 days" not in generate_navigation("all", "stars", CATEGORIES, SORT_TYPES)
