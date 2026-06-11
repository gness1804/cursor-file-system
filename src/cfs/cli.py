"""Main CLI entry point for the CFS tool."""

from pathlib import Path
from typing import Optional

import typer

from cfs import core
from cfs.cli_github_commands import gh_app
from cfs.cli_helpers import (
    _try_auto_close_github_issue,  # noqa: F401 - re-exported for test compatibility
    _try_auto_create_github_issue,  # noqa: F401 - re-exported for test compatibility
    console,
    handle_cfs_error,
)
from cfs.cli_instructions import (
    attach_categories_to,
    category_admin_app,
    exec_document_impl,
    handoff_app,
    instructions_app,
    view_all,
)
from cfs.cli_rules import rules_app
from cfs.exceptions import (
    CFSNotFoundError,
)

app = typer.Typer(
    name="cfs",
    help="Cursor File Structure (CFS) CLI - Manage Cursor instruction documents",
    add_completion=False,
)

# Register subcommand groups
app.add_typer(instructions_app, name="instructions")
app.add_typer(instructions_app, name="instr")  # Short alias for instructions
app.add_typer(instructions_app, name="i")  # Shorter alias for instructions
app.add_typer(rules_app, name="rules")
app.add_typer(gh_app, name="gh")

# Promote category command groups to the top level so `cfs bugs complete 7`
# works alongside the equivalent `cfs i bugs complete 7`. The instructions
# aliases above are permanent, not deprecated.
attach_categories_to(app)
app.add_typer(handoff_app, name="handoff")
app.add_typer(category_admin_app, name="category")


# Global options callback
@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
) -> None:
    """Main callback - shows help if no command provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def init(
    project_root: Optional[Path] = typer.Option(
        None,
        "--root",
        "-r",
        help="Project root directory (default: current directory)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Reinitialize even if CFS already exists",
    ),
) -> None:
    """Initialize CFS structure in current or specified directory."""
    root_path = (project_root or Path.cwd()).resolve()
    cursor_dir = root_path / ".cursor"

    # Check if CFS already exists
    if cursor_dir.exists() and cursor_dir.is_dir():
        if not force:
            console.print(
                f"[yellow]CFS already exists at {cursor_dir}[/yellow]",
            )
            if not typer.confirm("Reinitialize? (existing files will be preserved)"):
                console.print("[green]Skipping initialization[/green]")
                raise typer.Abort()
        else:
            console.print(f"[yellow]Reinitializing CFS at {cursor_dir}[/yellow]")

    # Create .cursor directory
    cursor_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]Created {cursor_dir}[/green]")

    # Create all category directories
    for category in sorted(core.VALID_CATEGORIES):
        category_path = cursor_dir / category
        category_path.mkdir(exist_ok=True)

    # Create init.md if it doesn't exist
    init_file = cursor_dir / "init.md"
    if not init_file.exists():
        # Detect project type for better boilerplate
        from cfs.cli_rules import _detect_repo_type

        repo_type = _detect_repo_type(cursor_dir)
        language_info = ""
        if repo_type.get("language"):
            language_info = f"\n**Primary Language**: {repo_type['language']}"
            if repo_type.get("framework"):
                language_info += f"\n**Framework**: {repo_type['framework']}"
            if repo_type.get("package_manager"):
                language_info += f"\n**Package Manager**: {repo_type['package_manager']}"

        init_content = f"""# CFS Initialization

This project uses CFS (Cursor File Structure) to manage instruction documents.{language_info}

## Structure

- `.cursor/rules/` - Cursor rules documents (.mdc files)
- `.cursor/features/` - Feature request documents
- `.cursor/bugs/` - Bug report documents
- `.cursor/refactors/` - Refactoring task documents
- `.cursor/ui/` - UI/UX task documents
- `.cursor/docs/` - Documentation task documents
- `.cursor/research/` - Research task documents
- `.cursor/progress/` - Progress and handoff documents
- `.cursor/qa/` - QA task documents
- `.cursor/security/` - Security-related documents
- `.cursor/infrastructure-and-deployment/` - Infrastructure and deployment task documents
- `.cursor/tmp/` - Temporary documents

## Usage

```bash
cfs features create   # Create a feature request
cfs bugs create       # Create a bug report
cfs view              # View incomplete documents (--all for everything)
cfs gh sync           # Sync with GitHub issues
```
"""
        init_file.write_text(init_content, encoding="utf-8")

    console.print(f"[green]✓ CFS initialized at {cursor_dir}[/green]")
    console.print(
        f"[dim]Created {len(core.VALID_CATEGORIES)} category directories[/dim]",
    )


@app.command()
def version() -> None:
    """Show the version number."""
    from cfs import __version__

    typer.echo(f"cfs version {__version__}")


def _format_tree_entry(path: Path, name: str) -> str:
    """Format a tree entry, highlighting incomplete issues in bold color."""
    if path.is_file() and path.suffix == ".md":
        try:
            from cfs.documents import parse_document_id
        except ImportError:
            return name

        parsed_id = parse_document_id(path.name)
        if parsed_id is not None:
            stem = path.stem
            if not stem.startswith(f"{parsed_id}-DONE-"):
                return f"[bold orange3]{name}[/]"

    return name


def _generate_tree(path: Path, prefix: str = "", is_last: bool = True) -> str:
    """Generate a tree structure string for a directory.

    Args:
        path: Path to the directory or file.
        prefix: Prefix string for the current level (for indentation).
        is_last: Whether this is the last item at its level.

    Returns:
        Tree structure string.
    """
    # Get the name to display
    name = path.name if path.name else str(path)
    if not name:  # Root directory case
        name = ".cursor"

    # Determine the connector and next prefix
    connector = "└── " if is_last else "├── "
    next_prefix = prefix + ("    " if is_last else "│   ")

    formatted_name = _format_tree_entry(path, name)
    result = prefix + connector + formatted_name + "\n"

    # If it's a directory, recurse into it
    if path.is_dir():
        try:
            # Get all items, sorted: directories first, then files
            items = sorted(
                path.iterdir(),
                key=lambda p: (p.is_file(), p.name.lower()),
            )

            for i, item in enumerate(items):
                is_last_item = i == len(items) - 1
                result += _generate_tree(item, next_prefix, is_last_item)
        except PermissionError:
            # Skip directories we can't access
            pass

    return result


@app.command("tree")
def tree() -> None:
    """Show the full file tree of the .cursor folder including empty folders.

    This command provides a quick reference for developers to see the complete
    structure of the CFS directory, including all categories and files.
    """
    try:
        # Find CFS root
        cfs_root = core.find_cfs_root()
    except CFSNotFoundError as e:
        handle_cfs_error(e)
        raise typer.Abort()

    # Generate and display the tree
    tree_output = _generate_tree(cfs_root, "", True)
    console.print(tree_output)


# Top-level view command (same semantics as `cfs i view`)
@app.command("view")
def view_incomplete(
    all_docs: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Include completed/closed documents",
    ),
    incomplete_only: bool = typer.Option(
        False,
        "--incomplete-only",
        "-i",
        hidden=True,
        help="Deprecated: incomplete documents are now shown by default",
    ),
) -> None:
    """View incomplete documents across all categories (use --all to include completed)."""
    view_all(category=None, all_docs=all_docs, incomplete_only=incomplete_only)


@app.command("exec")
def exec_document(
    category: str = typer.Argument(..., help="Category name"),
    doc_id: Optional[str] = typer.Argument(
        None,
        help="Document ID (numeric or 'next') - if not provided and --next not used, will prompt",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
    next_flag: bool = typer.Option(
        False,
        "--next",
        help="Execute the next (first) document in the category",
    ),
    claude: bool = typer.Option(
        False,
        "--claude",
        "-c",
        help="Start a Claude Code session with this document",
    ),
    gemini: bool = typer.Option(
        False,
        "--gemini",
        "-g",
        help="Start a Gemini CLI session with this document",
    ),
    cursor: bool = typer.Option(
        False,
        "--cursor",
        "-u",
        help="Start a Cursor Agent CLI session with this document",
    ),
    codex: bool = typer.Option(
        False,
        "--codex",
        "-x",
        help="Start an OpenAI Codex CLI session with this document",
    ),
) -> None:
    """Execute instructions from a document by outputting them as custom instructions text.

    This command reads a document and outputs its content as custom instructions that can be
    given to a Cursor agent. Use AI service flags to start a session directly.

    Also available as `cfs i <category> exec <id>`.

    Examples:
        cfs exec bugs 1          # Execute document with ID 1 in bugs category
        cfs exec bugs next       # Execute the next document in bugs category
        cfs exec bugs --next     # Same as above, using flag
        cfs exec bugs 1 --claude # Start Claude Code session with document
        cfs exec bugs 1 --gemini # Start Gemini CLI session with document
        cfs exec bugs 1 --cursor # Start Cursor Agent CLI session with document
        cfs exec bugs 1 --codex  # Start OpenAI Codex CLI session with document
    """
    exec_document_impl(category, doc_id, force, next_flag, claude, gemini, cursor, codex)


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
