"""GitHub integration commands for the CFS CLI."""

from typing import List, Optional

import typer

from cfs import core
from cfs.cli_helpers import console, handle_cfs_error
from cfs.exceptions import CFSNotFoundError

gh_app = typer.Typer(
    name="gh",
    help="GitHub integration - sync CFS documents with GitHub issues",
)


@gh_app.command("sync")
def gh_sync(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be done without making changes"
    ),
    include_categories: Optional[List[str]] = typer.Option(
        None,
        "--include-category",
        "-ic",
        help="Force-include a category that is excluded by default (e.g. security). Can be used multiple times.",
    ),
    exclude_categories: Optional[List[str]] = typer.Option(
        None,
        "--exclude-category",
        "-ec",
        help="Exclude an additional category from sync. Can be used multiple times.",
    ),
) -> None:
    """Synchronize CFS documents with GitHub issues.

    This command performs bidirectional sync:
    - Creates CFS documents for new GitHub issues
    - Creates GitHub issues for new CFS documents
    - Syncs status changes (close/complete)
    - Detects and helps resolve content conflicts

    By default, the 'tmp' and 'security' categories are excluded from sync.
    Use --include-category to override default exclusions, or --exclude-category
    to exclude additional categories.
    """
    from cfs.github import (
        GitHubAuthError,
        check_gh_authenticated,
        check_gh_installed,
        list_issues,
    )
    from cfs.sync import (
        build_sync_plan,
        compute_sync_categories,
        display_sync_results,
        display_sync_status,
        execute_sync_plan,
    )

    # Compute effective sync categories
    inc = set(include_categories) if include_categories else None
    exc = set(exclude_categories) if exclude_categories else None
    sync_cats = compute_sync_categories(inc, exc)

    # Validate user-provided categories
    for cat_list in [include_categories, exclude_categories]:
        if cat_list:
            for cat in cat_list:
                if cat not in core.VALID_CATEGORIES:
                    console.print(f"[red]Error: Invalid category '{cat}'[/red]")
                    console.print(
                        f"[yellow]Valid categories: {', '.join(sorted(core.VALID_CATEGORIES))}[/yellow]"
                    )
                    raise typer.Exit(1)

    # Check prerequisites
    if not check_gh_installed():
        console.print(
            "[red]Error: GitHub CLI (gh) is not installed.[/red]\n"
            "[yellow]Please install it from https://cli.github.com/[/yellow]"
        )
        raise typer.Exit(1)

    if not check_gh_authenticated():
        console.print(
            "[red]Error: GitHub CLI is not authenticated.[/red]\n"
            "[yellow]Please run 'gh auth login' first.[/yellow]"
        )
        raise typer.Exit(1)

    # Find CFS root
    try:
        cfs_root = core.find_cfs_root()
    except CFSNotFoundError as e:
        handle_cfs_error(e)
        raise typer.Exit(1)

    # Show which categories are being synced if non-default
    if inc or exc:
        console.print(f"[dim]Syncing categories: {', '.join(sorted(sync_cats))}[/dim]")

    # Get GitHub issues
    console.print("[dim]Fetching GitHub issues...[/dim]")
    try:
        github_issues = list_issues(state="all", limit=500)
    except GitHubAuthError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    console.print(f"[dim]Found {len(github_issues)} GitHub issues[/dim]")

    # Build sync plan
    console.print("[dim]Building sync plan...[/dim]")
    plan = build_sync_plan(cfs_root, github_issues, sync_categories=sync_cats)

    # Display status
    display_sync_status(console, plan)

    if not plan.has_actions():
        console.print("\n[green]Everything is in sync![/green]")
        return

    # Execute sync
    if dry_run:
        console.print("\n[yellow]Dry run mode - no changes will be made[/yellow]")

    results = execute_sync_plan(console, cfs_root, plan, dry_run=dry_run)

    # Display results
    console.print()
    display_sync_results(console, results)


@gh_app.command("status")
def gh_status(
    include_categories: Optional[List[str]] = typer.Option(
        None,
        "--include-category",
        "-ic",
        help="Force-include a category that is excluded by default (e.g. security). Can be used multiple times.",
    ),
    exclude_categories: Optional[List[str]] = typer.Option(
        None,
        "--exclude-category",
        "-ec",
        help="Exclude an additional category from sync. Can be used multiple times.",
    ),
) -> None:
    """Show sync status between CFS documents and GitHub issues.

    By default, the 'tmp' and 'security' categories are excluded from sync.
    Use --include-category to override default exclusions, or --exclude-category
    to exclude additional categories.
    """
    from cfs.github import (
        GitHubAuthError,
        check_gh_authenticated,
        check_gh_installed,
        list_issues,
    )
    from cfs.sync import build_sync_plan, compute_sync_categories, display_sync_status

    # Compute effective sync categories
    inc = set(include_categories) if include_categories else None
    exc = set(exclude_categories) if exclude_categories else None
    sync_cats = compute_sync_categories(inc, exc)

    # Validate user-provided categories
    for cat_list in [include_categories, exclude_categories]:
        if cat_list:
            for cat in cat_list:
                if cat not in core.VALID_CATEGORIES:
                    console.print(f"[red]Error: Invalid category '{cat}'[/red]")
                    console.print(
                        f"[yellow]Valid categories: {', '.join(sorted(core.VALID_CATEGORIES))}[/yellow]"
                    )
                    raise typer.Exit(1)

    # Check prerequisites
    if not check_gh_installed():
        console.print(
            "[red]Error: GitHub CLI (gh) is not installed.[/red]\n"
            "[yellow]Please install it from https://cli.github.com/[/yellow]"
        )
        raise typer.Exit(1)

    if not check_gh_authenticated():
        console.print(
            "[red]Error: GitHub CLI is not authenticated.[/red]\n"
            "[yellow]Please run 'gh auth login' first.[/yellow]"
        )
        raise typer.Exit(1)

    # Find CFS root
    try:
        cfs_root = core.find_cfs_root()
    except CFSNotFoundError as e:
        handle_cfs_error(e)
        raise typer.Exit(1)

    # Show which categories are being synced if non-default
    if inc or exc:
        console.print(f"[dim]Syncing categories: {', '.join(sorted(sync_cats))}[/dim]")

    # Get GitHub issues
    console.print("[dim]Fetching GitHub issues...[/dim]")
    try:
        github_issues = list_issues(state="all", limit=500)
    except GitHubAuthError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    # Build sync plan and display status
    plan = build_sync_plan(cfs_root, github_issues, sync_categories=sync_cats)
    display_sync_status(console, plan)


@gh_app.command("link")
def gh_link(
    category: str = typer.Argument(..., help="Category of the CFS document"),
    doc_id: int = typer.Argument(..., help="ID of the CFS document"),
    issue_number: int = typer.Argument(..., help="GitHub issue number to link to"),
) -> None:
    """Manually link a CFS document to a GitHub issue.

    This adds a github_issue field to the document's frontmatter.
    """
    from cfs import documents
    from cfs.github import add_labels, ensure_label_exists, get_cfs_label_for_category

    # Validate category
    if category not in core.VALID_CATEGORIES:
        console.print(f"[red]Error: Invalid category '{category}'[/red]")
        console.print(
            f"[yellow]Valid categories: {', '.join(sorted(core.VALID_CATEGORIES))}[/yellow]"
        )
        raise typer.Exit(1)

    # Find CFS root
    try:
        cfs_root = core.find_cfs_root()
    except CFSNotFoundError as e:
        handle_cfs_error(e)
        raise typer.Exit(1)

    category_path = core.get_category_path(cfs_root, category)

    # Find the document
    doc_path = documents.find_document_by_id(category_path, doc_id)
    if doc_path is None:
        console.print(f"[red]Error: Document {doc_id} not found in {category}[/red]")
        raise typer.Exit(1)

    # Read and update document
    try:
        content = doc_path.read_text(encoding="utf-8")

        # Check if already linked
        existing_issue = documents.get_github_issue_number(content)
        if existing_issue is not None:
            console.print(
                f"[yellow]Document is already linked to GitHub #{existing_issue}[/yellow]"
            )
            if existing_issue == issue_number:
                return
            console.print(f"[yellow]Updating link to #{issue_number}[/yellow]")

        # Add/update the link
        updated_content = documents.set_github_issue_number(content, issue_number)
        doc_path.write_text(updated_content, encoding="utf-8")

        # Add CFS label to GitHub issue
        label = get_cfs_label_for_category(category)
        ensure_label_exists(label)
        add_labels(issue_number, [label])

        console.print(f"[green]Linked {category}/{doc_id} to GitHub #{issue_number}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@gh_app.command("unlink")
def gh_unlink(
    category: str = typer.Argument(..., help="Category of the CFS document"),
    doc_id: int = typer.Argument(..., help="ID of the CFS document"),
) -> None:
    """Remove the GitHub issue link from a CFS document.

    This removes the github_issue field from the document's frontmatter.
    """
    from cfs import documents

    # Validate category
    if category not in core.VALID_CATEGORIES:
        console.print(f"[red]Error: Invalid category '{category}'[/red]")
        console.print(
            f"[yellow]Valid categories: {', '.join(sorted(core.VALID_CATEGORIES))}[/yellow]"
        )
        raise typer.Exit(1)

    # Find CFS root
    try:
        cfs_root = core.find_cfs_root()
    except CFSNotFoundError as e:
        handle_cfs_error(e)
        raise typer.Exit(1)

    category_path = core.get_category_path(cfs_root, category)

    # Find the document
    doc_path = documents.find_document_by_id(category_path, doc_id)
    if doc_path is None:
        console.print(f"[red]Error: Document {doc_id} not found in {category}[/red]")
        raise typer.Exit(1)

    # Read and update document
    try:
        content = doc_path.read_text(encoding="utf-8")

        # Check if linked
        existing_issue = documents.get_github_issue_number(content)
        if existing_issue is None:
            console.print(
                f"[yellow]Document {category}/{doc_id} is not linked to any GitHub issue[/yellow]"
            )
            return

        # Remove the link
        updated_content = documents.remove_github_issue_link(content)
        doc_path.write_text(updated_content, encoding="utf-8")

        console.print(
            f"[green]Removed GitHub link from {category}/{doc_id} (was #{existing_issue})[/green]"
        )
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@gh_app.command("purge-excluded")
def gh_purge_excluded(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be done without making changes"
    ),
    include_categories: Optional[List[str]] = typer.Option(
        None,
        "--include-category",
        "-ic",
        help="Force-include a category (won't be purged). Can be used multiple times.",
    ),
    exclude_categories: Optional[List[str]] = typer.Option(
        None,
        "--exclude-category",
        "-ec",
        help="Exclude an additional category (will be purged). Can be used multiple times.",
    ),
) -> None:
    """Delete GitHub issues for excluded categories and unlink CFS documents.

    This finds all CFS documents in excluded categories that are linked to
    GitHub issues, deletes those issues from GitHub, and removes the link
    from the CFS documents (preserving the documents themselves).

    By default, excluded categories are 'tmp' and 'security'.
    Use --include-category and --exclude-category to customize.
    """
    from cfs.github import (
        check_gh_authenticated,
        check_gh_installed,
        delete_issue,
    )
    from cfs.sync import compute_sync_categories

    # Compute which categories are excluded (i.e. what to purge)
    inc = set(include_categories) if include_categories else None
    exc = set(exclude_categories) if exclude_categories else None
    sync_cats = compute_sync_categories(inc, exc)
    excluded_cats = core.VALID_CATEGORIES - sync_cats

    # Validate user-provided categories
    for cat_list in [include_categories, exclude_categories]:
        if cat_list:
            for cat in cat_list:
                if cat not in core.VALID_CATEGORIES:
                    console.print(f"[red]Error: Invalid category '{cat}'[/red]")
                    console.print(
                        f"[yellow]Valid categories: {', '.join(sorted(core.VALID_CATEGORIES))}[/yellow]"
                    )
                    raise typer.Exit(1)

    if not excluded_cats:
        console.print("[yellow]No categories are excluded. Nothing to purge.[/yellow]")
        return

    # Check prerequisites
    if not check_gh_installed():
        console.print(
            "[red]Error: GitHub CLI (gh) is not installed.[/red]\n"
            "[yellow]Please install it from https://cli.github.com/[/yellow]"
        )
        raise typer.Exit(1)

    if not check_gh_authenticated():
        console.print(
            "[red]Error: GitHub CLI is not authenticated.[/red]\n"
            "[yellow]Please run 'gh auth login' first.[/yellow]"
        )
        raise typer.Exit(1)

    # Find CFS root
    try:
        cfs_root = core.find_cfs_root()
    except CFSNotFoundError as e:
        handle_cfs_error(e)
        raise typer.Exit(1)

    console.print(
        f"[yellow]Purging GitHub issues for excluded categories: "
        f"{', '.join(sorted(excluded_cats))}[/yellow]"
    )

    # Find linked documents in excluded categories
    from cfs.documents import (
        get_github_issue_number,
        list_documents,
        remove_github_issue_link,
    )

    purge_items = []  # List of (category, doc_id, doc_path, issue_number)
    for category in sorted(excluded_cats):
        docs = list_documents(cfs_root, category)
        if category not in docs:
            continue
        for doc in docs[category]:
            doc_path = doc["path"]
            try:
                content = doc_path.read_text(encoding="utf-8")
                issue_num = get_github_issue_number(content)
                if issue_num is not None:
                    purge_items.append((category, doc["id"], doc_path, issue_num))
            except (OSError, IOError):
                continue

    if not purge_items:
        console.print("[green]No linked documents found in excluded categories.[/green]")
        return

    # Display what will be purged
    from rich.table import Table

    table = Table(title="Issues to Purge")
    table.add_column("Category", style="cyan")
    table.add_column("Doc ID", style="green")
    table.add_column("GitHub Issue", style="red")

    for category, doc_id, doc_path, issue_num in purge_items:
        table.add_row(category, str(doc_id), f"#{issue_num}")

    console.print(table)

    if dry_run:
        console.print(
            f"\n[yellow]Dry run: would delete {len(purge_items)} GitHub issue(s) "
            f"and unlink the corresponding CFS documents.[/yellow]"
        )
        return

    # Confirm before proceeding (this is destructive)
    console.print(
        f"\n[bold red]This will permanently delete {len(purge_items)} GitHub issue(s).[/bold red]"
    )
    confirm = typer.confirm("Are you sure you want to proceed?")
    if not confirm:
        console.print("[yellow]Aborted.[/yellow]")
        return

    # Execute purge
    deleted = 0
    errors = 0
    for category, doc_id, doc_path, issue_num in purge_items:
        try:
            # Delete the GitHub issue
            delete_issue(issue_num)

            # Unlink the CFS document
            content = doc_path.read_text(encoding="utf-8")
            updated_content = remove_github_issue_link(content)
            doc_path.write_text(updated_content, encoding="utf-8")

            console.print(
                f"[green]Deleted GitHub #{issue_num} and unlinked {category}/{doc_id}[/green]"
            )
            deleted += 1
        except Exception as e:
            console.print(f"[red]Error purging {category}/{doc_id} (#{issue_num}): {e}[/red]")
            errors += 1

    console.print(f"\n[green]Purged {deleted} issue(s).[/green]", end="")
    if errors:
        console.print(f" [red]{errors} error(s).[/red]")
    else:
        console.print()


@gh_app.command("dedup")
def gh_dedup(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be removed without making changes"
    ),
) -> None:
    """Remove duplicate CFS documents across all synced categories.

    When duplicate document IDs or titles are found, keeps the best version
    (DONE/CLOSED preferred, then most recently modified) and removes the rest.

    Duplicates can arise when a file rename operation is interrupted mid-way
    during a complete or close operation.  Run this command to clean up, then
    re-run 'cfs gh sync' to restore a consistent state.
    """
    from cfs.documents import check_duplicates, remove_duplicate_documents
    from cfs.sync import SYNC_CATEGORIES

    try:
        cfs_root = core.find_cfs_root()
    except CFSNotFoundError as e:
        handle_cfs_error(e)
        raise typer.Exit(1)

    total_removed = 0
    total_errors = 0

    for category in sorted(SYNC_CATEGORIES):
        category_path = core.get_category_path(cfs_root, category)
        issues = check_duplicates(category_path)
        if not issues:
            continue

        console.print(f"\n[yellow]{category}[/yellow]")
        for issue in issues:
            console.print(f"  [red]{issue}[/red]")

        actions = remove_duplicate_documents(category_path, dry_run=dry_run)
        for action in actions:
            if "error" in action:
                console.print(
                    f"  [red]Error removing {action['path'].name}: {action['error']}[/red]"
                )
                total_errors += 1
            else:
                verb = "Would remove" if dry_run else "Removed"
                console.print(
                    f"  [green]{verb} {action['path'].name}[/green] "
                    f"(kept {action['kept'].name})"
                )
                if not dry_run:
                    total_removed += 1

    if total_removed == 0 and total_errors == 0 and not dry_run:
        console.print("[green]No duplicates found.[/green]")
    elif not dry_run:
        console.print(f"\n[green]Removed {total_removed} duplicate file(s).[/green]", end="")
        if total_errors:
            console.print(f" [red]{total_errors} error(s).[/red]")
        else:
            console.print()
