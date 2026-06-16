#!/usr/bin/env python3
"""Tests for scripts/readme/svg_templates/ – badges, toc, headers, dividers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.readme.svg_templates.badges import (  # noqa: E402
    generate_resource_badge_svg,
    render_flat_category_badge_svg,
    render_flat_sort_badge_svg,
)
from scripts.readme.svg_templates.dividers import (  # noqa: E402
    generate_desc_box_light_svg,
    generate_entry_separator_svg,
    generate_section_divider_light_svg,
)
from scripts.readme.svg_templates.headers import (  # noqa: E402
    generate_category_header_light_svg,
    render_h2_svg,
    render_h3_svg,
)
from scripts.readme.svg_templates.toc import (  # noqa: E402
    _normalize_svg_root,
    generate_toc_header_light_svg,
    generate_toc_row_light_svg,
    generate_toc_row_svg,
    generate_toc_sub_light_svg,
    generate_toc_sub_svg,
)


# ===========================================================================
# badges.py
# ===========================================================================

class TestGenerateResourceBadgeSvg:
    def test_returns_svg_string(self):
        result = generate_resource_badge_svg("My Tool")
        assert result.strip().startswith("<svg")
        assert "</svg>" in result

    def test_display_name_in_output(self):
        result = generate_resource_badge_svg("My Tool")
        assert "My Tool" in result

    def test_author_name_in_output(self):
        result = generate_resource_badge_svg("Tool", "Alice")
        assert "Alice" in result

    def test_no_author_no_author_element(self):
        result = generate_resource_badge_svg("Tool", "")
        assert 'class="author"' not in result

    def test_xml_entities_escaped_in_name(self):
        result = generate_resource_badge_svg("Tom & Jerry", "")
        assert "&amp;" in result
        assert "& Jerry" not in result

    def test_xml_entities_escaped_in_author(self):
        result = generate_resource_badge_svg("Tool", "A & B")
        assert "&amp;" in result

    def test_less_than_escaped(self):
        result = generate_resource_badge_svg("<Tool>")
        assert "&lt;" in result
        assert "&gt;" in result

    def test_quotes_escaped(self):
        result = generate_resource_badge_svg('Say "hello"')
        assert "&quot;" in result

    def test_initials_two_words(self):
        result = generate_resource_badge_svg("My Tool")
        assert "MT" in result

    def test_initials_single_word(self):
        result = generate_resource_badge_svg("Toolbox")
        assert "TO" in result

    def test_svg_width_minimum_220(self):
        # Very short name should still produce min-width SVG
        result = generate_resource_badge_svg("X")
        assert 'width="220"' in result

    def test_svg_width_maximum_700(self):
        long_name = "A" * 100
        result = generate_resource_badge_svg(long_name)
        assert 'width="700"' in result

    def test_svg_width_scales_with_name_length(self):
        short = generate_resource_badge_svg("AB")
        medium = generate_resource_badge_svg("A" * 30)
        # Extract width values
        import re
        short_w = int(re.search(r'<svg width="(\d+)"', short).group(1))
        medium_w = int(re.search(r'<svg width="(\d+)"', medium).group(1))
        assert medium_w >= short_w


class TestRenderFlatSortBadgeSvg:
    def test_returns_svg_string(self):
        result = render_flat_sort_badge_svg("Stars", "#FFD700")
        assert result.strip().startswith("<svg")
        assert "</svg>" in result

    def test_display_text_in_output(self):
        result = render_flat_sort_badge_svg("Stars", "#FFD700")
        assert "Stars" in result

    def test_color_in_output(self):
        result = render_flat_sort_badge_svg("Stars", "#FFD700")
        assert "#FFD700" in result

    def test_fixed_dimensions(self):
        result = render_flat_sort_badge_svg("Stars", "#FFD700")
        assert 'width="180"' in result
        assert 'height="48"' in result


class TestRenderFlatCategoryBadgeSvg:
    def test_returns_svg_string(self):
        result = render_flat_category_badge_svg("Tooling", "#4682B4", 100)
        assert result.strip().startswith("<svg")
        assert "</svg>" in result

    def test_display_text_in_output(self):
        result = render_flat_category_badge_svg("Tooling", "#4682B4", 100)
        assert "Tooling" in result

    def test_width_parameter_applied(self):
        result = render_flat_category_badge_svg("Tooling", "#4682B4", 150)
        assert 'width="150"' in result

    def test_color_in_output(self):
        result = render_flat_category_badge_svg("Tooling", "#4682B4", 100)
        assert "#4682B4" in result


# ===========================================================================
# toc.py
# ===========================================================================

class TestGenerateTocRowSvg:
    def test_returns_svg_string(self):
        result = generate_toc_row_svg("skills/", "Agent Skills")
        assert result.strip().startswith("<svg")

    def test_directory_name_in_output(self):
        result = generate_toc_row_svg("skills/", "Agent Skills")
        assert "skills/" in result

    def test_xml_entities_escaped(self):
        result = generate_toc_row_svg("a&b/", "desc")
        assert "&amp;" in result
        assert "a&b/" not in result

    def test_less_than_greater_than_escaped(self):
        result = generate_toc_row_svg("<dir>/", "desc")
        assert "&lt;" in result

    def test_crt_style_background(self):
        result = generate_toc_row_svg("dir/", "desc")
        assert "phosphor" in result  # CRT phosphor gradient


class TestGenerateTocRowLightSvg:
    def test_returns_svg_string(self):
        result = generate_toc_row_light_svg("skills/", "desc")
        assert result.strip().startswith("<svg")

    def test_directory_name_in_output(self):
        result = generate_toc_row_light_svg("tooling/", "desc")
        assert "tooling/" in result

    def test_xml_entities_escaped(self):
        result = generate_toc_row_light_svg("tom&jerry/", "desc")
        assert "&amp;" in result


class TestGenerateTocSubSvg:
    def test_returns_svg_string(self):
        result = generate_toc_sub_svg("general/", "desc")
        assert result.strip().startswith("<svg")

    def test_name_in_output(self):
        result = generate_toc_sub_svg("ide/", "desc")
        assert "ide/" in result

    def test_xml_escaping(self):
        result = generate_toc_sub_svg("a<b/", "desc")
        assert "&lt;" in result


class TestGenerateTocSubLightSvg:
    def test_returns_svg_string(self):
        result = generate_toc_sub_light_svg("general/", "desc")
        assert result.strip().startswith("<svg")

    def test_name_in_output(self):
        result = generate_toc_sub_light_svg("general/", "desc")
        assert "general/" in result


class TestGenerateTocHeaderLightSvg:
    def test_returns_svg_string(self):
        result = generate_toc_header_light_svg()
        assert result.strip().startswith("<svg")

    def test_contains_contents_label(self):
        result = generate_toc_header_light_svg()
        assert "CONTENTS" in result


class TestNormalizeSvgRoot:
    def test_replaces_existing_width(self):
        tag = '<svg width="999" height="40">'
        result = _normalize_svg_root(tag, 400, 40)
        assert 'width="400"' in result
        assert 'width="999"' not in result

    def test_replaces_existing_height(self):
        tag = '<svg width="400" height="999">'
        result = _normalize_svg_root(tag, 400, 40)
        assert 'height="40"' in result
        assert 'height="999"' not in result

    def test_adds_missing_width(self):
        tag = '<svg xmlns="http://www.w3.org/2000/svg">'
        result = _normalize_svg_root(tag, 400, 40)
        assert 'width="400"' in result

    def test_adds_missing_height(self):
        tag = '<svg xmlns="http://www.w3.org/2000/svg">'
        result = _normalize_svg_root(tag, 400, 40)
        assert 'height="40"' in result

    def test_sets_viewbox(self):
        tag = '<svg width="400" height="40">'
        result = _normalize_svg_root(tag, 400, 40)
        assert 'viewBox="0 0 400 40"' in result

    def test_replaces_existing_viewbox(self):
        tag = '<svg width="400" height="40" viewBox="0 0 999 999">'
        result = _normalize_svg_root(tag, 400, 40)
        assert 'viewBox="0 0 400 40"' in result
        assert 'viewBox="0 0 999 999"' not in result

    def test_sets_preserve_aspect_ratio(self):
        tag = '<svg width="400" height="40">'
        result = _normalize_svg_root(tag, 400, 40)
        assert 'preserveAspectRatio="xMinYMid meet"' in result

    def test_replaces_existing_preserve_aspect_ratio(self):
        tag = '<svg width="400" height="40" preserveAspectRatio="xMidYMid meet">'
        result = _normalize_svg_root(tag, 400, 40)
        assert 'preserveAspectRatio="xMinYMid meet"' in result
        assert '"xMidYMid meet"' not in result

    def test_result_closes_correctly(self):
        tag = '<svg width="400" height="40">'
        result = _normalize_svg_root(tag, 400, 40)
        assert result.endswith(">")


# ===========================================================================
# headers.py
# ===========================================================================

class TestRenderH2Svg:
    def test_returns_svg_string(self):
        result = render_h2_svg("Agent Skills")
        assert result.strip().startswith("<svg")

    def test_text_in_output(self):
        result = render_h2_svg("Agent Skills")
        assert "Agent Skills" in result

    def test_xml_entities_escaped(self):
        result = render_h2_svg("Tools & Tricks")
        assert "&amp;" in result

    def test_icon_included_in_output(self):
        result = render_h2_svg("Tooling", icon="🔧")
        assert "🔧" in result

    def test_no_icon_no_icon_in_text(self):
        result = render_h2_svg("Tooling")
        # Should not crash and text should be there
        assert "Tooling" in result

    def test_viewbox_includes_text_content(self):
        # Short title should have narrower viewBox than long title
        import re
        short_result = render_h2_svg("AB")
        long_result = render_h2_svg("A" * 40)
        # left_bound can be negative for long text, so allow optional minus sign
        short_vb = re.search(r'viewBox="-?\d+ 0 (\d+) \d+"', short_result)
        long_vb = re.search(r'viewBox="-?\d+ 0 (\d+) \d+"', long_result)
        assert short_vb is not None
        assert long_vb is not None
        short_width = int(short_vb.group(1))
        long_width = int(long_vb.group(1))
        assert long_width >= short_width

    def test_lt_gt_escaped(self):
        result = render_h2_svg("<Header>")
        assert "&lt;" in result
        assert "&gt;" in result


class TestRenderH3Svg:
    def test_returns_svg_string(self):
        result = render_h3_svg("General")
        assert result.strip().startswith("<svg")

    def test_text_in_output(self):
        result = render_h3_svg("IDE Integrations")
        assert "IDE Integrations" in result

    def test_xml_entities_escaped(self):
        result = render_h3_svg("A & B")
        assert "&amp;" in result

    def test_viewbox_width_scales_with_text(self):
        import re
        short = render_h3_svg("AB")
        long = render_h3_svg("A" * 50)
        short_w = int(re.search(r'viewBox="0 0 (\d+)', short).group(1))
        long_w = int(re.search(r'viewBox="0 0 (\d+)', long).group(1))
        assert long_w > short_w


class TestGenerateCategoryHeaderLightSvg:
    def test_returns_svg_string(self):
        result = generate_category_header_light_svg("Tooling")
        assert result.strip().startswith("<svg")

    def test_title_in_output(self):
        result = generate_category_header_light_svg("Tooling")
        assert "Tooling" in result

    def test_section_number_in_output(self):
        result = generate_category_header_light_svg("Tooling", section_number="07")
        assert "07" in result

    def test_default_section_number_is_01(self):
        result = generate_category_header_light_svg("Tooling")
        assert "01" in result

    def test_xml_entities_escaped(self):
        result = generate_category_header_light_svg("Tools & Tricks")
        assert "&amp;" in result


# ===========================================================================
# dividers.py
# ===========================================================================

class TestGenerateSectionDividerLightSvg:
    @pytest.mark.parametrize("variant", [1, 2, 3])
    def test_returns_svg_string_for_each_variant(self, variant):
        result = generate_section_divider_light_svg(variant)
        assert result.strip().startswith("<svg")
        assert "</svg>" in result

    def test_variant_1_has_nodes(self):
        result = generate_section_divider_light_svg(1)
        assert "circle" in result

    def test_variant_2_has_wave_path(self):
        result = generate_section_divider_light_svg(2)
        assert "<path" in result

    def test_variant_3_has_bracket_paths(self):
        result = generate_section_divider_light_svg(3)
        assert "<path" in result

    def test_unknown_variant_falls_back_to_variant_3(self):
        result = generate_section_divider_light_svg(99)
        # Should return something (not crash)
        assert isinstance(result, str)
        assert "<svg" in result


class TestGenerateDescBoxLightSvg:
    def test_top_returns_svg(self):
        result = generate_desc_box_light_svg("top")
        assert result.strip().startswith("<svg")

    def test_bottom_returns_svg(self):
        result = generate_desc_box_light_svg("bottom")
        assert result.strip().startswith("<svg")

    def test_top_and_bottom_differ(self):
        top = generate_desc_box_light_svg("top")
        bottom = generate_desc_box_light_svg("bottom")
        assert top != bottom


class TestGenerateEntrySeperatorSvg:
    def test_returns_svg_string(self):
        result = generate_entry_separator_svg()
        assert result.strip().startswith("<svg")
        assert "</svg>" in result

    def test_small_dimensions(self):
        result = generate_entry_separator_svg()
        assert 'width="200"' in result
        assert 'height="12"' in result
