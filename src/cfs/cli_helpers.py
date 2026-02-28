"""Shared helper functions for the CFS CLI."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from cfs.exceptions import (
    CFSError,
    CFSNotFoundError,
    DocumentNotFoundError,
    DocumentOperationError,
    InvalidCategoryError,
    InvalidDocumentIDError,
)

console = Console()


def get_document_notes(doc: dict, doc_list: list[dict]) -> str:
    """Generate notes/warning message for a document.

    Args:
        doc: Document dictionary with 'conforms_to_naming' and 'title' keys.
        doc_list: List of all documents in the same category.

    Returns:
        Notes string with warning if document doesn't conform to naming convention,
        empty string otherwise.
    """
    if doc.get("conforms_to_naming", True):
        return ""

    from cfs.documents import kebab_case

    suggested_name = kebab_case(doc["title"])
    # Find next available ID from conforming documents in this category
    conforming_ids = [d["id"] for d in doc_list if d.get("conforms_to_naming", True)]
    next_id = max(conforming_ids, default=0) + 1
    return f"[yellow]⚠️  Rename to: {next_id}-{suggested_name}.md[/yellow]"


def handle_cfs_error(error: CFSError) -> None:
    """Handle CFS-specific errors with user-friendly messages.

    Args:
        error: The CFS error to handle.
    """
    if isinstance(error, CFSNotFoundError):
        console.print(f"[red]Error: {error.message}[/red]")
    elif isinstance(error, InvalidCategoryError):
        console.print(f"[red]Error: Invalid category '{error.category}'[/red]")
        console.print(
            f"[yellow]Valid categories: {', '.join(sorted(error.valid_categories))}[/yellow]",
        )
    elif isinstance(error, DocumentNotFoundError):
        console.print(
            f"[red]Error: Document with ID {error.doc_id} not found in '{error.category}' category[/red]",
        )
        console.print(
            f"[yellow]Use 'cfs instructions {error.category} view' to list available documents[/yellow]",
        )
    elif isinstance(error, InvalidDocumentIDError):
        console.print(f"[red]Error: {error.message}[/red]")
        console.print(
            "[yellow]Document ID should be a number (e.g., 1) or a filename (e.g., 1-title.md)[/yellow]",
        )
    elif isinstance(error, DocumentOperationError):
        console.print(f"[red]Error: Failed to {error.operation}[/red]")
        console.print(f"[red]{error.message}[/red]")
    else:
        console.print(f"[red]Error: {error}[/red]")


def prompt_editor_selection(title: str) -> Optional[tuple[str, list[str]]]:
    """Prompt user to select an editor for editing a document.

    Args:
        title: The document title (for display in the prompt).

    Returns:
        Tuple of (editor_command, editor_args) if user selects an editor,
        None if user chooses not to edit.
    """
    from cfs import editor as editor_module

    available_editors = editor_module.get_available_editors()
    default_editor = editor_module.detect_editor()

    # Build options list
    console.print()
    console.print(f"[bold]Select an editor for '{title}':[/bold]")
    console.print()
    console.print("  [cyan]0[/cyan]  Don't edit")
    console.print(f"  [cyan]1[/cyan]  Default editor ({default_editor})")

    # Add available editors
    option_map: dict[int, tuple[str, list[str]]] = {
        1: (default_editor, []),
    }
    for idx, (display_name, cmd, args) in enumerate(available_editors, start=2):
        console.print(f"  [cyan]{idx}[/cyan]  {display_name}")
        option_map[idx] = (cmd, args)

    console.print()

    # Get user selection
    max_option = len(available_editors) + 1
    while True:
        try:
            choice = typer.prompt("Enter choice", default="0")
            choice_int = int(choice)
            if choice_int == 0:
                return None
            if 1 <= choice_int <= max_option:
                return option_map[choice_int]
            console.print(f"[red]Please enter a number between 0 and {max_option}[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number[/red]")


# =============================================================================
# GitHub Auto-Sync Helpers
# =============================================================================


def _try_auto_create_github_issue(category: str, doc_path: Path, title: str) -> None:
    """Attempt to auto-create a GitHub issue for a new CFS document.

    Silently skips if gh is not installed, not authenticated, or if the
    category is excluded from GitHub sync. All errors are reported as warnings.

    Args:
        category: CFS category name (e.g. "features", "bugs").
        doc_path: Path to the newly created CFS document.
        title: Document title (used as the GitHub issue title).
    """
    from cfs.documents import (
        build_github_issue_body,
        get_github_issue_number,
        set_github_issue_number,
    )
    from cfs.github import (
        GitHubError,
        check_gh_authenticated,
        check_gh_installed,
        create_issue,
        ensure_label_exists,
        get_cfs_label_for_category,
    )
    from cfs.sync import DEFAULT_EXCLUDED_CATEGORIES

    # Skip categories that are excluded from GitHub sync by default
    if category in DEFAULT_EXCLUDED_CATEGORIES:
        return

    # Check if gh is available and authenticated (silently skip if not)
    try:
        if not check_gh_installed():
            return
        if not check_gh_authenticated():
            return
    except Exception:
        return

    try:
        # Read current document content
        content = doc_path.read_text(encoding="utf-8")

        # Skip if document is already linked to a GitHub issue
        if get_github_issue_number(content) is not None:
            return

        # Build issue body from document sections
        body = build_github_issue_body(content)
        label = get_cfs_label_for_category(category)

        # Ensure the category label exists (best-effort; ignore failures)
        try:
            ensure_label_exists(label)
        except Exception:
            pass

        # Create the GitHub issue
        issue = create_issue(title, body, labels=[label])

        # Update the document with the github_issue frontmatter link
        updated_content = set_github_issue_number(content, issue.number)
        doc_path.write_text(updated_content, encoding="utf-8")

        console.print(f"[green]✓ Created GitHub issue #{issue.number}: {issue.url}[/green]")
    except GitHubError as e:
        console.print(f"[yellow]⚠️  GitHub auto-sync skipped: {e}[/yellow]")
    except Exception as e:
        console.print(f"[yellow]⚠️  GitHub auto-sync skipped: {e}[/yellow]")


def _try_auto_close_github_issue(doc_path: Path) -> None:
    """Attempt to auto-close a linked GitHub issue when a CFS document is completed/closed.

    Silently skips if gh is not installed, not authenticated, the document has
    no linked GitHub issue, or the issue is already closed.

    Args:
        doc_path: Path to the completed/closed CFS document.
    """
    from cfs.documents import get_github_issue_number
    from cfs.github import (
        GitHubError,
        check_gh_authenticated,
        check_gh_installed,
        close_issue,
        get_issue,
    )

    try:
        # Read the document to check for a linked GitHub issue
        content = doc_path.read_text(encoding="utf-8")
        issue_num = get_github_issue_number(content)
        if issue_num is None:
            return

        # Check if gh is available and authenticated (silently skip if not)
        if not check_gh_installed():
            return
        if not check_gh_authenticated():
            return

        # Check if the issue is already closed (avoid redundant API call)
        issue = get_issue(issue_num)
        if issue.state.lower() == "closed":
            return

        # Close the GitHub issue
        close_issue(issue_num)
        console.print(f"[green]✓ Closed GitHub issue #{issue_num}[/green]")
    except GitHubError as e:
        console.print(f"[yellow]⚠️  GitHub auto-sync skipped: {e}[/yellow]")
    except Exception as e:
        console.print(f"[yellow]⚠️  GitHub auto-sync skipped: {e}[/yellow]")
