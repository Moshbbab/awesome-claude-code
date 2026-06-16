#!/usr/bin/env python3
"""Tests for scripts/maintenance/check_repo_health.py."""

from __future__ import annotations

import csv
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.maintenance.check_repo_health import (  # noqa: E402
    check_repos_health,
    get_repo_info,
    is_outdated,
)


# ---------------------------------------------------------------------------
# is_outdated
# ---------------------------------------------------------------------------

class TestIsOutdated:
    def test_recent_date_not_outdated(self):
        recent = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert is_outdated(recent, months_threshold=6) is False

    def test_old_date_is_outdated(self):
        old = (datetime.now(UTC) - timedelta(days=200)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert is_outdated(old, months_threshold=6) is True

    def test_none_date_is_outdated(self):
        assert is_outdated(None, months_threshold=6) is True

    def test_empty_string_date_is_outdated(self):
        assert is_outdated("", months_threshold=6) is True

    def test_malformed_date_is_outdated(self):
        assert is_outdated("not-a-date", months_threshold=6) is True

    def test_z_suffix_parsed_correctly(self):
        recent = (datetime.now(UTC) - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert is_outdated(recent, months_threshold=6) is False

    def test_different_thresholds(self):
        one_month_ago = (datetime.now(UTC) - timedelta(days=35)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert is_outdated(one_month_ago, months_threshold=1) is True
        assert is_outdated(one_month_ago, months_threshold=3) is False

    def test_threshold_uses_30_days_per_month(self):
        just_over_boundary = (datetime.now(UTC) - timedelta(days=181)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        assert is_outdated(just_over_boundary, months_threshold=6) is True


# ---------------------------------------------------------------------------
# get_repo_info
# ---------------------------------------------------------------------------

class TestGetRepoInfo:
    def _mock(self, status: int, json_data: dict | None = None):
        m = MagicMock()
        m.status_code = status
        m.json.return_value = json_data or {}
        return m

    def test_200_returns_repo_data(self):
        payload = {"open_issues_count": 5, "pushed_at": "2024-01-01T00:00:00Z"}
        with patch("scripts.maintenance.check_repo_health.requests.get",
                   return_value=self._mock(200, payload)):
            result = get_repo_info("owner", "repo")
        assert result["exists"] is True
        assert result["open_issues"] == 5
        assert result["last_updated"] == "2024-01-01T00:00:00Z"

    def test_404_returns_not_found(self):
        with patch("scripts.maintenance.check_repo_health.requests.get",
                   return_value=self._mock(404)):
            result = get_repo_info("owner", "deleted-repo")
        assert result["exists"] is False
        assert result["last_updated"] is None

    def test_403_returns_none(self):
        with patch("scripts.maintenance.check_repo_health.requests.get",
                   return_value=self._mock(403)):
            assert get_repo_info("owner", "repo") is None

    def test_500_returns_none(self):
        with patch("scripts.maintenance.check_repo_health.requests.get",
                   return_value=self._mock(500)):
            assert get_repo_info("owner", "repo") is None

    def test_network_error_returns_none(self):
        import requests as req
        with patch("scripts.maintenance.check_repo_health.requests.get",
                   side_effect=req.exceptions.RequestException("error")):
            assert get_repo_info("owner", "repo") is None

    def test_fallback_open_issues_key(self):
        payload = {"open_issues": 3, "pushed_at": "2024-01-01T00:00:00Z"}
        with patch("scripts.maintenance.check_repo_health.requests.get",
                   return_value=self._mock(200, payload)):
            result = get_repo_info("owner", "repo")
        assert result["open_issues"] == 3

    def test_request_has_timeout(self):
        with patch("scripts.maintenance.check_repo_health.requests.get",
                   return_value=self._mock(200, {"open_issues_count": 0,
                                                  "pushed_at": "2024-01-01T00:00:00Z"})) as m:
            get_repo_info("owner", "repo")
            _, kwargs = m.call_args
            assert "timeout" in kwargs


# ---------------------------------------------------------------------------
# check_repos_health
# ---------------------------------------------------------------------------

class TestCheckReposHealth:
    def _csv(self, tmp_path: Path, rows: list[dict]) -> Path:
        f = tmp_path / "resources.csv"
        fieldnames = ["Display Name", "Primary Link", "Active"]
        with open(f, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        return f

    def _healthy(self):
        m = MagicMock()
        m.status_code = 200
        m.json.return_value = {
            "open_issues_count": 1,
            "pushed_at": (datetime.now(UTC) - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        return m

    def _stale(self):
        m = MagicMock()
        m.status_code = 200
        m.json.return_value = {
            "open_issues_count": 5,
            "pushed_at": (datetime.now(UTC) - timedelta(days=300)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        return m

    def test_healthy_repo_not_problematic(self, tmp_path):
        f = self._csv(tmp_path, [{
            "Display Name": "Repo", "Primary Link": "https://github.com/o/r", "Active": "TRUE"
        }])
        with patch("scripts.maintenance.check_repo_health.requests.get", return_value=self._healthy()):
            assert check_repos_health(f) == []

    def test_stale_repo_with_many_issues_is_problematic(self, tmp_path):
        f = self._csv(tmp_path, [{
            "Display Name": "Repo", "Primary Link": "https://github.com/o/r", "Active": "TRUE"
        }])
        with patch("scripts.maintenance.check_repo_health.requests.get", return_value=self._stale()):
            result = check_repos_health(f)
        assert len(result) == 1
        assert result[0]["repo"] == "r"

    def test_active_false_rows_skipped(self, tmp_path):
        f = self._csv(tmp_path, [{
            "Display Name": "Repo", "Primary Link": "https://github.com/o/r", "Active": "FALSE"
        }])
        with patch("scripts.maintenance.check_repo_health.requests.get") as m:
            check_repos_health(f)
            assert m.call_count == 0

    def test_active_lowercase_true_is_normalized(self, tmp_path):
        """The code calls .upper() so lowercase 'true' is treated the same as 'TRUE'."""
        f = self._csv(tmp_path, [{
            "Display Name": "Repo", "Primary Link": "https://github.com/o/r", "Active": "true"
        }])
        with patch("scripts.maintenance.check_repo_health.requests.get",
                   return_value=self._healthy()) as m:
            check_repos_health(f)
            # 'true'.upper() == 'TRUE', so repo IS checked
            assert m.call_count == 1

    def test_non_github_links_skipped(self, tmp_path):
        f = self._csv(tmp_path, [{
            "Display Name": "Tool", "Primary Link": "https://example.com/tool", "Active": "TRUE"
        }])
        with patch("scripts.maintenance.check_repo_health.requests.get") as m:
            check_repos_health(f)
            assert m.call_count == 0

    def test_deleted_repo_not_in_problematic(self, tmp_path):
        f = self._csv(tmp_path, [{
            "Display Name": "Gone", "Primary Link": "https://github.com/o/gone", "Active": "TRUE"
        }])
        m = MagicMock()
        m.status_code = 404
        m.json.return_value = {}
        with patch("scripts.maintenance.check_repo_health.requests.get", return_value=m):
            assert check_repos_health(f) == []

    def test_api_error_skips_without_failing(self, tmp_path):
        f = self._csv(tmp_path, [{
            "Display Name": "Repo", "Primary Link": "https://github.com/o/r", "Active": "TRUE"
        }])
        m = MagicMock()
        m.status_code = 403
        with patch("scripts.maintenance.check_repo_health.requests.get", return_value=m):
            result = check_repos_health(f)
        assert isinstance(result, list)

    def test_missing_csv_raises_sys_exit(self, tmp_path):
        with pytest.raises(SystemExit):
            check_repos_health(tmp_path / "nonexistent.csv")

    def test_issues_at_threshold_not_problematic(self, tmp_path):
        """open_issues must be strictly > threshold to be problematic."""
        f = self._csv(tmp_path, [{
            "Display Name": "Repo", "Primary Link": "https://github.com/o/r", "Active": "TRUE"
        }])
        m = MagicMock()
        m.status_code = 200
        m.json.return_value = {
            "open_issues_count": 2,  # Equal to default threshold (not greater than)
            "pushed_at": (datetime.now(UTC) - timedelta(days=300)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        with patch("scripts.maintenance.check_repo_health.requests.get", return_value=m):
            result = check_repos_health(f, issues_threshold=2)
        assert result == []
