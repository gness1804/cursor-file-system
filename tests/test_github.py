"""Tests for the GitHub integration module."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from cfs.github import (
    GitHubAPIError,
    GitHubCLINotFoundError,
    GitHubIssue,
    _run_gh_command,
    check_gh_authenticated,
    check_gh_installed,
    get_category_from_cfs_label,
    get_cfs_label_for_category,
    get_repo_info,
)


class TestGitHubIssue:
    """Tests for GitHubIssue dataclass."""

    def test_from_dict_full_data(self):
        """Test creating GitHubIssue from complete API response."""
        data = {
            "number": 42,
            "title": "Test Issue",
            "body": "This is the body",
            "state": "open",
            "labels": [{"name": "bug"}, {"name": "cfs:features"}],
            "url": "https://github.com/owner/repo/issues/42",
        }
        issue = GitHubIssue.from_dict(data)

        assert issue.number == 42
        assert issue.title == "Test Issue"
        assert issue.body == "This is the body"
        assert issue.state == "open"
        assert issue.labels == ["bug", "cfs:features"]
        assert issue.url == "https://github.com/owner/repo/issues/42"

    def test_from_dict_minimal_data(self):
        """Test creating GitHubIssue from minimal API response."""
        data = {}
        issue = GitHubIssue.from_dict(data)

        assert issue.number == 0
        assert issue.title == ""
        assert issue.body == ""
        assert issue.state == "open"
        assert issue.labels == []
        assert issue.url == ""

    def test_from_dict_null_body(self):
        """Test that null body is converted to empty string."""
        data = {"number": 1, "body": None}
        issue = GitHubIssue.from_dict(data)
        assert issue.body == ""

    def test_from_dict_html_url_fallback(self):
        """Test that html_url is used when url is missing."""
        data = {"number": 1, "html_url": "https://github.com/owner/repo/issues/1"}
        issue = GitHubIssue.from_dict(data)
        assert issue.url == "https://github.com/owner/repo/issues/1"


class TestRunGhCommand:
    """Tests for _run_gh_command helper."""

    @patch("subprocess.run")
    def test_successful_command(self, mock_run):
        """Test successful gh command execution."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="output",
            stderr="",
        )

        result = _run_gh_command(["--version"])

        mock_run.assert_called_once()
        assert result.returncode == 0
        assert result.stdout == "output"

    @patch("subprocess.run")
    def test_gh_not_found(self, mock_run):
        """Test handling when gh CLI is not installed."""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(GitHubCLINotFoundError) as exc_info:
            _run_gh_command(["--version"])

        assert "not installed" in str(exc_info.value)

    @patch("subprocess.run")
    def test_command_failure_with_check(self, mock_run):
        """Test that failed command raises exception when check=True."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error message",
        )

        with pytest.raises(GitHubAPIError) as exc_info:
            _run_gh_command(["issue", "list"], check=True)

        assert "error message" in str(exc_info.value)

    @patch("subprocess.run")
    def test_command_failure_without_check(self, mock_run):
        """Test that failed command returns result when check=False."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error message",
        )

        result = _run_gh_command(["issue", "list"], check=False)
        assert result.returncode == 1

    @patch("subprocess.run")
    def test_command_timeout(self, mock_run):
        """Test handling of command timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="gh", timeout=30)

        with pytest.raises(GitHubAPIError) as exc_info:
            _run_gh_command(["issue", "list"])

        assert "timed out" in str(exc_info.value)


class TestCheckGhInstalled:
    """Tests for check_gh_installed function."""

    @patch("cfs.github._run_gh_command")
    def test_gh_installed(self, mock_run):
        """Test when gh CLI is installed."""
        mock_run.return_value = MagicMock(returncode=0)
        assert check_gh_installed() is True

    @patch("cfs.github._run_gh_command")
    def test_gh_not_installed(self, mock_run):
        """Test when gh CLI is not installed."""
        mock_run.side_effect = GitHubCLINotFoundError("not installed")
        assert check_gh_installed() is False


class TestCheckGhAuthenticated:
    """Tests for check_gh_authenticated function."""

    @patch("cfs.github._run_gh_command")
    def test_authenticated(self, mock_run):
        """Test when gh CLI is authenticated."""
        mock_run.return_value = MagicMock(returncode=0)
        assert check_gh_authenticated() is True

    @patch("cfs.github._run_gh_command")
    def test_not_authenticated(self, mock_run):
        """Test when gh CLI is not authenticated."""
        mock_run.return_value = MagicMock(returncode=1)
        assert check_gh_authenticated() is False


class TestGetRepoInfo:
    """Tests for get_repo_info function."""

    @patch("cfs.github._run_gh_command")
    def test_valid_repo(self, mock_run):
        """Test getting repo info from valid repository."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"owner": {"login": "testowner"}, "name": "testrepo"}',
        )

        result = get_repo_info()
        assert result == ("testowner", "testrepo")

    @patch("cfs.github._run_gh_command")
    def test_not_in_repo(self, mock_run):
        """Test when not in a git repository."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        result = get_repo_info()
        assert result is None

    @patch("cfs.github._run_gh_command")
    def test_invalid_json(self, mock_run):
        """Test handling of invalid JSON response."""
        mock_run.return_value = MagicMock(returncode=0, stdout="not json")

        result = get_repo_info()
        assert result is None


class TestLabelHelpers:
    """Tests for CFS label helper functions."""

    def test_get_cfs_label_for_category(self):
        """Test generating CFS label from category."""
        assert get_cfs_label_for_category("features") == "cfs:features"
        assert get_cfs_label_for_category("bugs") == "cfs:bugs"
        assert get_cfs_label_for_category("progress") == "cfs:progress"

    def test_get_category_from_cfs_label(self):
        """Test extracting category from CFS label."""
        assert get_category_from_cfs_label("cfs:features") == "features"
        assert get_category_from_cfs_label("cfs:bugs") == "bugs"

    def test_get_category_from_non_cfs_label(self):
        """Test that non-CFS labels return None."""
        assert get_category_from_cfs_label("bug") is None
        assert get_category_from_cfs_label("enhancement") is None
        assert get_category_from_cfs_label("CFS:features") is None  # Case sensitive


class TestDeleteIssue:
    """Tests for delete_issue function."""

    @patch("cfs.github.check_gh_authenticated", return_value=True)
    @patch("cfs.github._run_gh_command")
    def test_delete_issue_calls_gh(self, mock_run, mock_auth):
        """Test that delete_issue calls gh with correct args."""
        from cfs.github import delete_issue

        mock_run.return_value = MagicMock(returncode=0)
        delete_issue(42)
        mock_run.assert_called_once_with(["issue", "delete", "42", "--yes"])

    @patch("cfs.github.check_gh_authenticated", return_value=False)
    def test_delete_issue_requires_auth(self, mock_auth):
        """Test that delete_issue raises when not authenticated."""
        from cfs.github import GitHubAuthError, delete_issue

        with pytest.raises(GitHubAuthError):
            delete_issue(42)
