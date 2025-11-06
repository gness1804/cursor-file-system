"""Main CLI entry point for the CFS tool."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from cfs import core

app = typer.Typer(
    name="cfs",
    help="Cursor File Structure (CFS) CLI - Manage Cursor instruction documents",
    add_completion=False,
)

console = Console()

# Create subcommand groups
instructions_app = typer.Typer(
    name="instructions",
    help="Manage Cursor instruction documents",
)
rules_app = typer.Typer(
    name="rules",
    help="Manage Cursor rules documents",
)

# Register subcommand groups
app.add_typer(instructions_app, name="instructions")
app.add_typer(rules_app, name="rules")


# Dynamically create category subcommands for instructions
def create_category_commands() -> None:
    """Create commands for each category dynamically."""
    for category in core.VALID_CATEGORIES:
        # Skip 'rules' as it has its own command group
        if category == "rules":
            continue

        # Create a Typer app for this category
        category_app = typer.Typer(name=category, help=f"Manage {category} documents")
        instructions_app.add_typer(category_app, name=category)

        # Create all commands for this category with proper closure capture
        def make_category_commands(cat: str):
            """Factory function to create category-specific commands."""

            @category_app.command("create")
            def create_in_category(
                title: Optional[str] = typer.Option(
                    None,
                    "--title",
                    "-t",
                    help="Document title (if not provided, will prompt)",
                ),
                edit: bool = typer.Option(
                    False,
                    "--edit",
                    "-e",
                    help="Open editor immediately after creating",
                ),
            ) -> None:
                """Create a new document in this category."""
                # Find CFS root
                cfs_root = core.find_cfs_root()
                if cfs_root is None:
                    console.print(
                        "[red]Error: CFS structure not found. Run 'cfs init' first.[/red]",
                    )
                    raise typer.Abort()

                # Get category path
                category_path = core.get_category_path(cfs_root, cat)

                # Get title if not provided
                if title is None:
                    title = typer.prompt("Document title")
                    if not title.strip():
                        console.print("[red]Error: Title cannot be empty[/red]")
                        raise typer.Abort()

                # Get content - prompt if edit flag is set
                content = ""
                if edit:
                    from cfs import editor

                    console.print(f"[yellow]Opening editor for '{title}'...[/yellow]")
                    content = editor.edit_content()

                # Create document
                from cfs import documents

                try:
                    doc_path = documents.create_document(category_path, title, content)
                    console.print(
                        f"[green]✓ Created document: {doc_path}[/green]",
                    )
                except Exception as e:
                    console.print(f"[red]Error creating document: {e}[/red]")
                    raise typer.Abort()

            @category_app.command("edit")
            def edit_in_category(
                doc_id: str = typer.Argument(..., help="Document ID (numeric or filename)"),
            ) -> None:
                """Edit an existing document in this category."""
                from cfs import documents
                from cfs.documents import parse_document_id

                # Find CFS root
                cfs_root = core.find_cfs_root()
                if cfs_root is None:
                    console.print(
                        "[red]Error: CFS structure not found. Run 'cfs init' first.[/red]",
                    )
                    raise typer.Abort()

                # Get category path
                category_path = core.get_category_path(cfs_root, cat)

                # Parse ID (handle both numeric ID and filename)
                parsed_id = parse_document_id(doc_id)
                if parsed_id is None:
                    try:
                        parsed_id = int(doc_id)
                    except ValueError:
                        console.print(
                            f"[red]Error: Invalid document ID '{doc_id}'[/red]",
                        )
                        raise typer.Abort()

                # Get current content
                current_content = documents.get_document(category_path, parsed_id)
                if current_content is None:
                    console.print(
                        f"[red]Error: Document with ID {parsed_id} not found in {cat}[/red]",
                    )
                    raise typer.Abort()

                # Launch editor with current content
                from cfs import editor

                console.print(f"[yellow]Opening editor for document {parsed_id}...[/yellow]")
                edited_content = editor.edit_content(current_content)

                # Save updated content
                try:
                    doc_path = documents.edit_document(category_path, parsed_id, edited_content)
                    console.print(
                        f"[green]✓ Updated document: {doc_path}[/green]",
                    )
                except Exception as e:
                    console.print(f"[red]Error updating document: {e}[/red]")
                    raise typer.Abort()

            @category_app.command("delete")
            def delete_in_category(
                doc_id: str = typer.Argument(..., help="Document ID (numeric or filename)"),
                force: bool = typer.Option(
                    False,
                    "--force",
                    "-f",
                    help="Skip confirmation prompt",
                ),
            ) -> None:
                """Delete a document from this category."""
                from cfs import documents
                from cfs.documents import parse_document_id

                # Find CFS root
                cfs_root = core.find_cfs_root()
                if cfs_root is None:
                    console.print(
                        "[red]Error: CFS structure not found. Run 'cfs init' first.[/red]",
                    )
                    raise typer.Abort()

                # Get category path
                category_path = core.get_category_path(cfs_root, cat)

                # Parse ID (handle both numeric ID and filename)
                parsed_id = parse_document_id(doc_id)
                if parsed_id is None:
                    try:
                        parsed_id = int(doc_id)
                    except ValueError:
                        console.print(
                            f"[red]Error: Invalid document ID '{doc_id}'[/red]",
                        )
                        raise typer.Abort()

                # Find document to show preview
                doc_path = documents.find_document_by_id(category_path, parsed_id)
                if doc_path is None or not doc_path.exists():
                    console.print(
                        f"[red]Error: Document with ID {parsed_id} not found in {cat}[/red]",
                    )
                    raise typer.Abort()

                # Show document preview (first few lines)
                try:
                    content = doc_path.read_text(encoding="utf-8")
                    lines = content.split("\n")[:5]
                    preview = "\n".join(lines)
                    if len(content.split("\n")) > 5:
                        preview += "\n..."

                    console.print("\n[yellow]Document preview:[/yellow]")
                    console.print(f"[dim]{preview}[/dim]\n")
                except Exception:
                    pass

                # Confirm deletion
                if not force:
                    if not typer.confirm(
                        f"Are you sure you want to delete document {parsed_id}?",
                        default=False,
                    ):
                        console.print("[green]Deletion cancelled[/green]")
                        raise typer.Abort()

                # Delete document
                try:
                    deleted = documents.delete_document(category_path, parsed_id)
                    if deleted:
                        console.print(
                            f"[green]✓ Deleted document: {doc_path}[/green]",
                        )
                    else:
                        console.print(
                            "[red]Error: Document not found[/red]",
                        )
                        raise typer.Abort()
                except Exception as e:
                    console.print(f"[red]Error deleting document: {e}[/red]")
                    raise typer.Abort()

            @category_app.command("view")
            def view_in_category() -> None:
                """View all documents in this category."""
                from cfs import documents
                from datetime import datetime

                # Find CFS root
                cfs_root = core.find_cfs_root()
                if cfs_root is None:
                    console.print(
                        "[red]Error: CFS structure not found. Run 'cfs init' first.[/red]",
                    )
                    raise typer.Abort()

                # List documents in this category
                docs_dict = documents.list_documents(cfs_root, cat)
                doc_list = docs_dict.get(cat, [])

                if not doc_list:
                    console.print(f"[yellow]No documents found in {cat} category[/yellow]")
                    return

                # Create table
                table = Table(title=f"Documents in {cat}", box=box.ROUNDED)
                table.add_column("ID", style="cyan", no_wrap=True)
                table.add_column("Title", style="magenta")
                table.add_column("Size", justify="right", style="green")
                table.add_column("Modified", style="yellow")

                for doc in doc_list:
                    size_kb = doc["size"] / 1024
                    size_str = f"{size_kb:.1f} KB" if size_kb >= 1 else f"{doc['size']} B"
                    modified_time = datetime.fromtimestamp(doc["modified"])
                    modified_str = modified_time.strftime("%Y-%m-%d %H:%M")

                    table.add_row(
                        str(doc["id"]),
                        doc["title"],
                        size_str,
                        modified_str,
                    )

                console.print()
                console.print(table)

        # Create all commands for this category
        make_category_commands(category)


# Initialize category commands
create_category_commands()


# Top-level instructions commands
@instructions_app.command("view")
def view_all(
    category: Optional[str] = typer.Argument(
        None,
        help="Optional category name to filter by",
    ),
) -> None:
    """View all documents across all categories or a specific category."""
    from cfs import documents
    from datetime import datetime

    # Find CFS root
    cfs_root = core.find_cfs_root()
    if cfs_root is None:
        console.print(
            "[red]Error: CFS structure not found. Run 'cfs init' first.[/red]",
        )
        raise typer.Abort()

    # List documents
    docs_dict = documents.list_documents(cfs_root, category)

    if not docs_dict:
        if category:
            console.print(
                f"[yellow]No documents found in {category} category[/yellow]",
            )
        else:
            console.print("[yellow]No documents found[/yellow]")
        return

    # Create table(s)
    if category:
        # Single category view
        doc_list = docs_dict.get(category, [])
        if not doc_list:
            console.print(
                f"[yellow]No documents found in {category} category[/yellow]",
            )
            return

        table = Table(title=f"Documents in {category}", box=box.ROUNDED)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="magenta")
        table.add_column("Size", justify="right", style="green")
        table.add_column("Modified", style="yellow")

        for doc in doc_list:
            size_kb = doc["size"] / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb >= 1 else f"{doc['size']} B"
            modified_time = datetime.fromtimestamp(doc["modified"])
            modified_str = modified_time.strftime("%Y-%m-%d %H:%M")

            table.add_row(
                str(doc["id"]),
                doc["title"],
                size_str,
                modified_str,
            )

        console.print()
        console.print(table)
    else:
        # All categories view
        for cat, doc_list in sorted(docs_dict.items()):
            if not doc_list:
                continue

            console.print(f"\n[bold cyan]{cat.upper()}[/bold cyan]")
            table = Table(box=box.SIMPLE)
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Title", style="magenta")
            table.add_column("Size", justify="right", style="green")
            table.add_column("Modified", style="yellow")

            for doc in doc_list:
                size_kb = doc["size"] / 1024
                size_str = f"{size_kb:.1f} KB" if size_kb >= 1 else f"{doc['size']} B"
                modified_time = datetime.fromtimestamp(doc["modified"])
                modified_str = modified_time.strftime("%Y-%m-%d %H:%M")

                table.add_row(
                    str(doc["id"]),
                    doc["title"],
                    size_str,
                    modified_str,
                )

            console.print(table)


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
        init_content = """# CFS Initialization

This directory was initialized using the Cursor File Structure (CFS) CLI.

## Categories

- **rules/** - Rules used by Cursor (automatically read by Cursor agents)
- **research/** - Research-related documents
- **bugs/** - Bug investigation and fix instructions
- **features/** - Feature development documents
- **refactors/** - Refactoring-related documents
- **docs/** - Documentation creation instructions
- **progress/** - Progress tracking and handoff documents
- **qa/** - Testing and QA documents
- **tmp/** - Temporary files for Cursor agent use

## Usage

Use the `cfs` CLI tool to manage documents in these categories.

For help: `cfs --help`
"""
        init_file.write_text(init_content, encoding="utf-8")
        console.print(f"[green]Created {init_file}[/green]")

    console.print("\n[bold green]✓ CFS initialized successfully![/bold green]")


@app.command()
def version() -> None:
    """Show the version number."""
    from cfs import __version__

    typer.echo(f"cfs version {__version__}")


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
