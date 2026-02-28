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
    _launch_claude_code,
    _launch_codex,
    _launch_cursor_agent,
    _launch_gemini,
    instructions_app,
    view_all,
)
from cfs.cli_rules import rules_app
from cfs.exceptions import (
    CFSNotFoundError,
    DocumentNotFoundError,
    InvalidCategoryError,
    InvalidDocumentIDError,
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
- `.cursor/docs/` - Documentation task documents
- `.cursor/research/` - Research task documents
- `.cursor/progress/` - Progress and handoff documents
- `.cursor/qa/` - QA task documents
- `.cursor/security/` - Security-related documents
- `.cursor/tmp/` - Temporary documents

## Usage

```bash
cfs instructions features create  # Create a feature request
cfs instructions bugs create       # Create a bug report
cfs instructions view              # View all documents
cfs gh sync                        # Sync with GitHub issues
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


# Top-level view command (shortcut for `cfs i view -i`)
@app.command("view")
def view_incomplete() -> None:
    """View all incomplete documents across all categories.

    This is a shortcut for 'cfs i view -i'.
    """
    view_all(category=None, incomplete_only=True)


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

    Examples:
        cfs exec bugs 1          # Execute document with ID 1 in bugs category
        cfs exec bugs next       # Execute the next document in bugs category
        cfs exec bugs --next     # Same as above, using flag
        cfs exec bugs 1 --claude # Start Claude Code session with document
        cfs exec bugs 1 --gemini # Start Gemini CLI session with document
        cfs exec bugs 1 --cursor # Start Cursor Agent CLI session with document
        cfs exec bugs 1 --codex  # Start OpenAI Codex CLI session with document
    """
    from cfs.documents import (
        find_document_by_id,
        get_document_title,
        get_next_document_id,
        parse_document_id_from_string,
    )

    # Check for mutual exclusivity of AI service flags
    ai_flags = [
        ("--claude", claude),
        ("--gemini", gemini),
        ("--cursor", cursor),
        ("--codex", codex),
    ]
    selected_flags = [name for name, value in ai_flags if value]
    if len(selected_flags) > 1:
        console.print(
            f"[red]Error: Only one AI service flag can be used at a time. "
            f"You specified: {', '.join(selected_flags)}[/red]"
        )
        raise typer.Abort()

    try:
        # Find CFS root
        cfs_root = core.find_cfs_root()
    except CFSNotFoundError as e:
        handle_cfs_error(e)
        raise typer.Abort()

    # Validate category
    try:
        category_path = core.get_category_path(cfs_root, category)
    except InvalidCategoryError as e:
        handle_cfs_error(e)
        raise typer.Abort()

    # Determine which document to execute
    target_doc_id: Optional[int] = None

    if next_flag or (doc_id and doc_id.lower() == "next"):
        # Get next document
        target_doc_id = get_next_document_id(category_path)
        if target_doc_id is None:
            console.print(
                f"[yellow]No documents found in {category} category[/yellow]",
            )
            raise typer.Abort()
    elif doc_id:
        # Parse provided document ID
        try:
            target_doc_id = parse_document_id_from_string(doc_id)
        except InvalidDocumentIDError as e:
            handle_cfs_error(e)
            raise typer.Abort()
    else:
        # No doc_id provided and --next not used - prompt user
        console.print(
            "[yellow]No document ID provided. Use a number, 'next', or --next flag[/yellow]"
        )
        raise typer.Abort()

    # Find document
    doc_path = find_document_by_id(category_path, target_doc_id)
    if doc_path is None or not doc_path.exists():
        try:
            raise DocumentNotFoundError(target_doc_id, category)
        except DocumentNotFoundError as e:
            handle_cfs_error(e)
            raise typer.Abort()

    # Get document title and content
    try:
        title = get_document_title(doc_path)
        content = doc_path.read_text(encoding="utf-8")
    except (OSError, IOError) as e:
        console.print(f"[red]Error reading document: {e}[/red]")
        raise typer.Abort()

    # Determine which AI service is selected (if any)
    ai_service = None
    if claude:
        ai_service = "Claude Code"
    elif gemini:
        ai_service = "Gemini CLI"
    elif cursor:
        ai_service = "Cursor Agent CLI"
    elif codex:
        ai_service = "OpenAI Codex CLI"

    # Show confirmation (unless --force)
    if not force:
        console.print(f"\n[bold]Document:[/bold] {title}")
        console.print(f"[dim]Category: {category}, ID: {target_doc_id}[/dim]")
        console.print()
        if ai_service:
            confirm_msg = f"Start a {ai_service} session with this document?"
        else:
            confirm_msg = "Execute this document? (This will output the instructions text)"
        if not typer.confirm(confirm_msg, default=False):
            console.print("[yellow]Execution cancelled[/yellow]")
            raise typer.Abort()

    if claude:
        # Launch Claude Code with the document content
        _launch_claude_code(content, category, target_doc_id)
    elif gemini:
        # Launch Gemini CLI with the document content
        _launch_gemini(content, category, target_doc_id)
    elif cursor:
        # Launch Cursor Agent CLI with the document content
        _launch_cursor_agent(content, category, target_doc_id)
    elif codex:
        # Launch OpenAI Codex CLI with the document content
        _launch_codex(content, category, target_doc_id)
    else:
        # Output the document content as custom instructions
        console.print()
        console.print("[bold cyan]--- Custom Instructions ---[/bold cyan]")
        console.print()
        console.print(content)
        console.print()
        console.print("[bold cyan]--- End Custom Instructions ---[/bold cyan]")
        console.print()

        # Copy to clipboard
        try:
            import pyperclip

            pyperclip.copy(content)
            console.print("[green]✓ Instructions copied to clipboard[/green]")
        except ImportError:
            console.print(
                "[yellow]⚠️  pyperclip not available - cannot copy to clipboard automatically[/yellow]",
            )
            console.print(
                "[dim]Copy the instructions above and provide them to your Cursor agent.[/dim]",
            )
        except Exception as e:
            console.print(
                f"[yellow]⚠️  Could not copy to clipboard: {e}[/yellow]",
            )
            console.print(
                "[dim]Copy the instructions above and provide them to your Cursor agent.[/dim]",
            )


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
