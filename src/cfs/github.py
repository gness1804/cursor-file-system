"""GitHub integration module using the gh CLI."""

import json
import subprocess
from dataclasses import dataclass
from typing import List, Optional


class GitHubError(Exception):
    """Base exception for GitHub operations."""

    pass


class GitHubCLINotFoundError(GitHubError):
    """Raised when gh CLI is not installed."""

    pass


class GitHubAuthError(GitHubError):
    """Raised when gh CLI is not authenticated."""

    pass


class GitHubAPIError(GitHubError):
    """Raised when a GitHub API call fails."""

    pass


@dataclass
class GitHubIssue:
    """Represents a GitHub issue."""

    number: int
    title: str
    body: str
    state: str  # "open" or "closed"
    labels: List[str]
    url: str

    @classmethod
    def from_dict(cls, data: dict) -> "GitHubIssue":
        """Create GitHubIssue from API response dict."""
        return cls(
            number=data.get("number", 0),
            title=data.get("title", ""),
            body=data.get("body") or "",
            state=data.get("state", "open"),
            labels=[label.get("name", "") for label in data.get("labels", [])],
            url=data.get("url") or data.get("html_url", ""),
        )


def _run_gh_command(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a gh CLI command and return the result.

    Args:
        args: Arguments to pass to gh CLI.
        check: If True, raise exception on non-zero exit code.

    Returns:
        CompletedProcess with stdout/stderr.

    Raises:
        GitHubCLINotFoundError: If gh CLI is not installed.
        GitHubAPIError: If command fails and check is True.
    """
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if check and result.returncode != 0:
            raise GitHubAPIError(f"gh command failed: {result.stderr.strip()}")
        return result
    except FileNotFoundError:
        raise GitHubCLINotFoundError(
            "GitHub CLI (gh) is not installed. " "Please install it from https://cli.github.com/"
        )
    except subprocess.TimeoutExpired:
        raise GitHubAPIError("GitHub CLI command timed out")


def check_gh_installed() -> bool:
    """Check if gh CLI is installed.

    Returns:
        True if gh CLI is available, False otherwise.
    """
    try:
        _run_gh_command(["--version"], check=False)
        return True
    except GitHubCLINotFoundError:
        return False


def check_gh_authenticated() -> bool:
    """Check if gh CLI is authenticated.

    Returns:
        True if authenticated, False otherwise.

    Raises:
        GitHubCLINotFoundError: If gh CLI is not installed.
    """
    result = _run_gh_command(["auth", "status"], check=False)
    return result.returncode == 0


def get_repo_info() -> Optional[tuple]:
    """Get the current repository's owner and name from git remote.

    Returns:
        Tuple of (owner, repo) or None if not in a git repo or no remote.

    Raises:
        GitHubCLINotFoundError: If gh CLI is not installed.
    """
    try:
        result = _run_gh_command(
            ["repo", "view", "--json", "owner,name"],
            check=False,
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        owner = data.get("owner", {}).get("login")
        name = data.get("name")

        if owner and name:
            return (owner, name)
        return None
    except (json.JSONDecodeError, KeyError):
        return None


def list_issues(
    state: str = "all",
    labels: Optional[List[str]] = None,
    limit: int = 100,
) -> List[GitHubIssue]:
    """List GitHub issues for the current repository.

    Args:
        state: Filter by state: "open", "closed", or "all".
        labels: Optional list of labels to filter by.
        limit: Maximum number of issues to return.

    Returns:
        List of GitHubIssue objects.

    Raises:
        GitHubCLINotFoundError: If gh CLI is not installed.
        GitHubAuthError: If not authenticated.
        GitHubAPIError: If API call fails.
    """
    if not check_gh_authenticated():
        raise GitHubAuthError("gh CLI is not authenticated. Run 'gh auth login' first.")

    args = [
        "issue",
        "list",
        "--state",
        state,
        "--limit",
        str(limit),
        "--json",
        "number,title,body,state,labels,url",
    ]

    if labels:
        for label in labels:
            args.extend(["--label", label])

    result = _run_gh_command(args)

    try:
        data = json.loads(result.stdout)
        return [GitHubIssue.from_dict(issue) for issue in data]
    except json.JSONDecodeError as e:
        raise GitHubAPIError(f"Failed to parse GitHub response: {e}")


def get_issue(issue_number: int) -> GitHubIssue:
    """Get a specific GitHub issue by number.

    Args:
        issue_number: The issue number.

    Returns:
        GitHubIssue object.

    Raises:
        GitHubCLINotFoundError: If gh CLI is not installed.
        GitHubAuthError: If not authenticated.
        GitHubAPIError: If API call fails or issue not found.
    """
    if not check_gh_authenticated():
        raise GitHubAuthError("gh CLI is not authenticated. Run 'gh auth login' first.")

    result = _run_gh_command(
        [
            "issue",
            "view",
            str(issue_number),
            "--json",
            "number,title,body,state,labels,url",
        ]
    )

    try:
        data = json.loads(result.stdout)
        return GitHubIssue.from_dict(data)
    except json.JSONDecodeError as e:
        raise GitHubAPIError(f"Failed to parse GitHub response: {e}")


def create_issue(
    title: str,
    body: str,
    labels: Optional[List[str]] = None,
) -> GitHubIssue:
    """Create a new GitHub issue.

    Args:
        title: Issue title.
        body: Issue body (markdown).
        labels: Optional list of labels to add.

    Returns:
        Created GitHubIssue object.

    Raises:
        GitHubCLINotFoundError: If gh CLI is not installed.
        GitHubAuthError: If not authenticated.
        GitHubAPIError: If API call fails.
    """
    if not check_gh_authenticated():
        raise GitHubAuthError("gh CLI is not authenticated. Run 'gh auth login' first.")

    args = [
        "issue",
        "create",
        "--title",
        title,
        "--body",
        body,
    ]

    if labels:
        for label in labels:
            args.extend(["--label", label])

    result = _run_gh_command(args)

    # gh issue create outputs the URL of the created issue
    # We need to fetch the issue details
    issue_url = result.stdout.strip()

    # Extract issue number from URL (format: https://github.com/owner/repo/issues/123)
    try:
        issue_number = int(issue_url.rstrip("/").split("/")[-1])
        return get_issue(issue_number)
    except (ValueError, IndexError):
        raise GitHubAPIError(f"Failed to parse created issue URL: {issue_url}")


def close_issue(issue_number: int) -> GitHubIssue:
    """Close a GitHub issue.

    Args:
        issue_number: The issue number to close.

    Returns:
        Updated GitHubIssue object.

    Raises:
        GitHubCLINotFoundError: If gh CLI is not installed.
        GitHubAuthError: If not authenticated.
        GitHubAPIError: If API call fails.
    """
    if not check_gh_authenticated():
        raise GitHubAuthError("gh CLI is not authenticated. Run 'gh auth login' first.")

    _run_gh_command(["issue", "close", str(issue_number)])
    return get_issue(issue_number)


def delete_issue(issue_number: int) -> None:
    """Delete a GitHub issue permanently.

    Args:
        issue_number: The issue number to delete.

    Raises:
        GitHubCLINotFoundError: If gh CLI is not installed.
        GitHubAuthError: If not authenticated.
        GitHubAPIError: If API call fails.
    """
    if not check_gh_authenticated():
        raise GitHubAuthError("gh CLI is not authenticated. Run 'gh auth login' first.")

    _run_gh_command(["issue", "delete", str(issue_number), "--yes"])


def reopen_issue(issue_number: int) -> GitHubIssue:
    """Reopen a closed GitHub issue.

    Args:
        issue_number: The issue number to reopen.

    Returns:
        Updated GitHubIssue object.

    Raises:
        GitHubCLINotFoundError: If gh CLI is not installed.
        GitHubAuthError: If not authenticated.
        GitHubAPIError: If API call fails.
    """
    if not check_gh_authenticated():
        raise GitHubAuthError("gh CLI is not authenticated. Run 'gh auth login' first.")

    _run_gh_command(["issue", "reopen", str(issue_number)])
    return get_issue(issue_number)


def update_issue(
    issue_number: int,
    title: Optional[str] = None,
    body: Optional[str] = None,
) -> GitHubIssue:
    """Update a GitHub issue's title and/or body.

    Args:
        issue_number: The issue number to update.
        title: New title (optional).
        body: New body (optional).

    Returns:
        Updated GitHubIssue object.

    Raises:
        GitHubCLINotFoundError: If gh CLI is not installed.
        GitHubAuthError: If not authenticated.
        GitHubAPIError: If API call fails.
    """
    if not check_gh_authenticated():
        raise GitHubAuthError("gh CLI is not authenticated. Run 'gh auth login' first.")

    if title is None and body is None:
        return get_issue(issue_number)

    args = ["issue", "edit", str(issue_number)]

    if title is not None:
        args.extend(["--title", title])

    if body is not None:
        args.extend(["--body", body])

    _run_gh_command(args)
    return get_issue(issue_number)


def add_labels(issue_number: int, labels: List[str]) -> GitHubIssue:
    """Add labels to a GitHub issue.

    Args:
        issue_number: The issue number.
        labels: List of label names to add.

    Returns:
        Updated GitHubIssue object.

    Raises:
        GitHubCLINotFoundError: If gh CLI is not installed.
        GitHubAuthError: If not authenticated.
        GitHubAPIError: If API call fails.
    """
    if not check_gh_authenticated():
        raise GitHubAuthError("gh CLI is not authenticated. Run 'gh auth login' first.")

    if not labels:
        return get_issue(issue_number)

    args = ["issue", "edit", str(issue_number)]
    for label in labels:
        args.extend(["--add-label", label])

    _run_gh_command(args)
    return get_issue(issue_number)


def remove_labels(issue_number: int, labels: List[str]) -> GitHubIssue:
    """Remove labels from a GitHub issue.

    Args:
        issue_number: The issue number.
        labels: List of label names to remove.

    Returns:
        Updated GitHubIssue object.

    Raises:
        GitHubCLINotFoundError: If gh CLI is not installed.
        GitHubAuthError: If not authenticated.
        GitHubAPIError: If API call fails.
    """
    if not check_gh_authenticated():
        raise GitHubAuthError("gh CLI is not authenticated. Run 'gh auth login' first.")

    if not labels:
        return get_issue(issue_number)

    args = ["issue", "edit", str(issue_number)]
    for label in labels:
        args.extend(["--remove-label", label])

    _run_gh_command(args)
    return get_issue(issue_number)


def ensure_label_exists(label_name: str, color: str = "0366d6") -> bool:
    """Ensure a label exists in the repository, creating it if necessary.

    Args:
        label_name: The label name (e.g., "cfs:features").
        color: Hex color code without # (default: GitHub blue).

    Returns:
        True if label exists or was created successfully.

    Raises:
        GitHubCLINotFoundError: If gh CLI is not installed.
        GitHubAuthError: If not authenticated.
    """
    if not check_gh_authenticated():
        raise GitHubAuthError("gh CLI is not authenticated. Run 'gh auth login' first.")

    # Try to create the label (will fail silently if it already exists)
    result = _run_gh_command(
        ["label", "create", label_name, "--color", color, "--force"],
        check=False,
    )

    # --force flag should make this always succeed unless there's a permission issue
    return result.returncode == 0


def get_cfs_label_for_category(category: str) -> str:
    """Get the CFS label name for a category.

    Args:
        category: CFS category name (e.g., "features", "bugs").

    Returns:
        Label name in format "cfs:<category>".
    """
    return f"cfs:{category}"


def get_category_from_cfs_label(label: str) -> Optional[str]:
    """Extract CFS category from a label name.

    Args:
        label: Label name (e.g., "cfs:features").

    Returns:
        Category name if label is a CFS label, None otherwise.
    """
    if label.startswith("cfs:"):
        return label[4:]  # Remove "cfs:" prefix
    return None
