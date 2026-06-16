#!/usr/bin/env python3
"""Tests for scripts/categories/add_category.py – CategoryAdder logic."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.categories.add_category import CategoryAdder  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_YAML = {
    "categories": [
        {
            "id": "tooling",
            "name": "Tooling",
            "prefix": "tool",
            "icon": "🔧",
            "description": "Tools.",
            "order": 1,
            "subcategories": [{"id": "general", "name": "General"}],
        },
        {
            "id": "hooks",
            "name": "Hooks",
            "prefix": "hook",
            "icon": "🪝",
            "description": "Hooks.",
            "order": 2,
            "subcategories": [{"id": "general", "name": "General"}],
        },
    ]
}

MINIMAL_TEMPLATE = textwrap.dedent("""\
    id: category
    type: dropdown
    attributes:
      label: Category
      options:
        - Tooling
        - Hooks
        - Official Documentation
    validations:
      required: true
""")


@pytest.fixture
def repo_structure(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a minimal repo structure with categories.yaml and issue template."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    categories_file = templates_dir / "categories.yaml"
    with open(categories_file, "w", encoding="utf-8") as f:
        yaml.dump(MINIMAL_YAML, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    github_dir = tmp_path / ".github" / "ISSUE_TEMPLATE"
    github_dir.mkdir(parents=True)
    template_file = github_dir / "recommend-resource.yml"
    template_file.write_text(MINIMAL_TEMPLATE, encoding="utf-8")

    return tmp_path, categories_file, template_file


@pytest.fixture
def adder(repo_structure, monkeypatch: pytest.MonkeyPatch) -> CategoryAdder:
    """Return a CategoryAdder pointed at the temp repo structure."""
    repo_root, _, _ = repo_structure
    instance = CategoryAdder(repo_root)
    # Patch category_manager so it reads from the temp YAML, not the real one
    monkeypatch.setattr(
        "scripts.categories.add_category.category_manager",
        _build_mock_manager(repo_root / "templates" / "categories.yaml"),
    )
    return instance


def _build_mock_manager(yaml_path: Path):
    """Build a minimal mock of category_manager backed by the given YAML file."""

    class _Manager:
        def get_categories_for_readme(self):
            with open(yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data["categories"]

        def get_max_order(self):
            cats = self.get_categories_for_readme()
            return max(c.get("order", 0) for c in cats) if cats else 0

    return _Manager()


# ---------------------------------------------------------------------------
# get_max_order
# ---------------------------------------------------------------------------

class TestGetMaxOrder:
    def test_returns_max_of_existing_orders(self, adder):
        # MINIMAL_YAML has orders 1 and 2
        assert adder.get_max_order() == 2

    def test_empty_categories_returns_zero(self, repo_structure, monkeypatch):
        repo_root, _, _ = repo_structure

        class EmptyManager:
            def get_categories_for_readme(self):
                return []

        monkeypatch.setattr("scripts.categories.add_category.category_manager", EmptyManager())
        adder = CategoryAdder(repo_root)
        assert adder.get_max_order() == 0


# ---------------------------------------------------------------------------
# add_category_to_yaml
# ---------------------------------------------------------------------------

class TestAddCategoryToYaml:
    def test_new_category_appended(self, adder, repo_structure):
        _, categories_file, _ = repo_structure
        result = adder.add_category_to_yaml(
            category_id="new-cat",
            name="New Category",
            prefix="newcat",
            icon="⭐",
            description="A new category.",
        )
        assert result is True
        with open(categories_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        ids = [c["id"] for c in data["categories"]]
        assert "new-cat" in ids

    def test_duplicate_category_id_rejected(self, adder):
        result = adder.add_category_to_yaml(
            category_id="tooling",
            name="Tooling Duplicate",
            prefix="tool",
            icon="🔧",
            description="Dupe.",
        )
        assert result is False

    def test_order_defaults_to_max_plus_one(self, adder, repo_structure):
        _, categories_file, _ = repo_structure
        adder.add_category_to_yaml("new-cat", "New Cat", "new", "⭐", "Desc.")
        with open(categories_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        new_cat = next(c for c in data["categories"] if c["id"] == "new-cat")
        assert new_cat["order"] == 3  # max was 2, so 3

    def test_explicit_order_shifts_existing(self, adder, repo_structure):
        _, categories_file, _ = repo_structure
        # Insert at order 1 — existing cats (order 1 and 2) should be bumped up
        adder.add_category_to_yaml("first-cat", "First Cat", "first", "🥇", "Desc.", order=1)
        with open(categories_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        orders = {c["id"]: c["order"] for c in data["categories"]}
        assert orders["first-cat"] == 1
        assert orders["tooling"] == 2  # was 1, now bumped
        assert orders["hooks"] == 3    # was 2, now bumped

    def test_subcategories_default_to_general(self, adder, repo_structure):
        _, categories_file, _ = repo_structure
        adder.add_category_to_yaml("new-cat", "New Cat", "new", "⭐", "Desc.")
        with open(categories_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        new_cat = next(c for c in data["categories"] if c["id"] == "new-cat")
        assert new_cat["subcategories"] == [{"id": "general", "name": "General"}]

    def test_custom_subcategories_stored_correctly(self, adder, repo_structure):
        _, categories_file, _ = repo_structure
        adder.add_category_to_yaml(
            "new-cat", "New Cat", "new", "⭐", "Desc.",
            subcategories=["General", "Advanced"],
        )
        with open(categories_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        new_cat = next(c for c in data["categories"] if c["id"] == "new-cat")
        sub_names = [s["name"] for s in new_cat["subcategories"]]
        assert "General" in sub_names
        assert "Advanced" in sub_names

    def test_subcategory_id_is_slugified(self, adder, repo_structure):
        _, categories_file, _ = repo_structure
        adder.add_category_to_yaml(
            "new-cat", "New Cat", "new", "⭐", "Desc.",
            subcategories=["My Sub Cat"],
        )
        with open(categories_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        new_cat = next(c for c in data["categories"] if c["id"] == "new-cat")
        assert new_cat["subcategories"][0]["id"] == "my-sub-cat"

    def test_categories_sorted_by_order_after_write(self, adder, repo_structure):
        _, categories_file, _ = repo_structure
        adder.add_category_to_yaml("new-cat", "New Cat", "new", "⭐", "Desc.", order=1)
        with open(categories_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        orders = [c["order"] for c in data["categories"]]
        assert orders == sorted(orders)

    def test_missing_categories_key_returns_false(self, repo_structure, monkeypatch):
        repo_root, categories_file, _ = repo_structure
        # Valid YAML but missing the "categories" key
        categories_file.write_text("no_categories_key: true\n", encoding="utf-8")
        adder = CategoryAdder(repo_root)

        class FakeManager:
            def get_categories_for_readme(self):
                return []

        monkeypatch.setattr("scripts.categories.add_category.category_manager", FakeManager())
        result = adder.add_category_to_yaml("new", "New", "new", "⭐", "Desc.")
        assert result is False


# ---------------------------------------------------------------------------
# update_issue_template
# ---------------------------------------------------------------------------

class TestUpdateIssueTemplate:
    def test_new_category_added_before_official_documentation(self, adder, repo_structure):
        _, _, template_file = repo_structure
        result = adder.update_issue_template("New Category")
        assert result is True
        content = template_file.read_text(encoding="utf-8")
        assert "- New Category" in content
        # Must appear before Official Documentation
        pos_new = content.index("- New Category")
        pos_official = content.index("- Official Documentation")
        assert pos_new < pos_official

    def test_existing_category_not_duplicated(self, adder, repo_structure):
        _, _, template_file = repo_structure
        result = adder.update_issue_template("Tooling")
        assert result is True
        content = template_file.read_text(encoding="utf-8")
        assert content.count("- Tooling") == 1

    def test_missing_category_section_returns_false(self, repo_structure):
        repo_root, _, template_file = repo_structure
        template_file.write_text("no category section here\n", encoding="utf-8")
        adder = CategoryAdder(repo_root)
        result = adder.update_issue_template("Anything")
        assert result is False

    def test_template_file_written_back(self, adder, repo_structure):
        _, _, template_file = repo_structure
        before = template_file.read_text(encoding="utf-8")
        adder.update_issue_template("Brand New Category")
        after = template_file.read_text(encoding="utf-8")
        assert after != before
        assert "Brand New Category" in after
