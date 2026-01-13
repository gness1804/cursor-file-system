"""Main CLI entry point for the CFS tool."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from cfs import core
from cfs.exceptions import (
    CFSError,
    CFSNotFoundError,
    InvalidCategoryError,
    DocumentNotFoundError,
    InvalidDocumentIDError,
    DocumentOperationError,
)

app = typer.Typer(
    name="cfs",
    help="Cursor File Structure (CFS) CLI - Manage Cursor instruction documents",
    add_completion=False,
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


# Create subcommand groups
instructions_app = typer.Typer(
    name="instructions",
    help="Manage Cursor instruction documents",
)
rules_app = typer.Typer(
    name="rules",
    help="Manage Cursor rules documents",
)
handoff_app = typer.Typer(
    name="handoff",
    help="Create and manage handoff documents for agent transitions",
    invoke_without_command=True,
)

# Register subcommand groups
app.add_typer(instructions_app, name="instructions")
app.add_typer(instructions_app, name="instr")  # Short alias for instructions
app.add_typer(instructions_app, name="i")  # Shorter alias for instructions
app.add_typer(rules_app, name="rules")
instructions_app.add_typer(handoff_app, name="handoff")


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
                from cfs import documents

                try:
                    # Find CFS root
                    cfs_root = core.find_cfs_root()
                except CFSNotFoundError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                try:
                    # Get category path
                    category_path = core.get_category_path(cfs_root, cat)
                except InvalidCategoryError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                # Get title if not provided
                if title is None:
                    title = typer.prompt("Document title")
                    if not title.strip():
                        console.print("[red]Error: Title cannot be empty[/red]")
                        raise typer.Abort()

                # Get repository root (parent of .cursor directory)
                repo_root = cfs_root.parent

                # Generate initial structured content
                from cfs.documents import kebab_case, title_case

                kebab_title = kebab_case(title)
                title_case_title = title_case(kebab_title)

                # Format the repository path for display (use ~ for home directory if applicable)
                try:
                    repo_path_str = str(repo_root.resolve())
                    home_dir = Path.home()
                    if repo_path_str.startswith(str(home_dir)):
                        repo_path_str = "~" + repo_path_str[len(str(home_dir)) :]
                except Exception:
                    repo_path_str = str(repo_root)

                # Build initial document structure
                initial_content_lines = [
                    f"# {title_case_title}",
                    "",
                    "## Working directory",
                    "",
                    f"`{repo_path_str}`",
                    "",
                    "## Contents",
                    "",
                    "## Acceptance criteria",
                    "",
                ]
                initial_content = "\n".join(initial_content_lines)

                # Get content - prompt if edit flag is set, or ask user if not set
                content = initial_content
                if edit:
                    from cfs import editor

                    console.print(f"[yellow]Opening editor for '{title}'...[/yellow]")
                    content = editor.edit_content(initial_content)
                else:
                    # Prompt user: edit now or create empty?
                    if typer.confirm(
                        f"Would you like to edit '{title}' now?",
                        default=False,
                    ):
                        from cfs import editor

                        console.print(f"[yellow]Opening editor for '{title}'...[/yellow]")
                        content = editor.edit_content(initial_content)

                # Create document with the full content (user may have edited the structure)
                try:
                    doc_path = documents.create_document(category_path, title, content, repo_root)
                    console.print(
                        f"[green]✓ Created document: {doc_path}[/green]",
                    )
                except (DocumentOperationError, ValueError) as e:
                    if isinstance(e, DocumentOperationError):
                        handle_cfs_error(e)
                    else:
                        console.print(f"[red]Error: {e}[/red]")
                    raise typer.Abort()

            @category_app.command("edit")
            def edit_in_category(
                doc_id: str = typer.Argument(..., help="Document ID (numeric or filename)"),
            ) -> None:
                """Edit an existing document in this category."""
                from cfs import documents
                from cfs.documents import parse_document_id_from_string
                from cfs import editor

                try:
                    # Find CFS root
                    cfs_root = core.find_cfs_root()
                except CFSNotFoundError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                try:
                    # Get category path
                    category_path = core.get_category_path(cfs_root, cat)
                except InvalidCategoryError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                # Parse ID (handle both numeric ID and filename)
                try:
                    parsed_id = parse_document_id_from_string(doc_id)
                except InvalidDocumentIDError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                # Get current content
                try:
                    current_content = documents.get_document(category_path, parsed_id)
                except DocumentNotFoundError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()
                except DocumentOperationError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                # Launch editor with current content
                console.print(f"[yellow]Opening editor for document {parsed_id}...[/yellow]")
                edited_content = editor.edit_content(current_content)

                # Save updated content
                try:
                    doc_path = documents.edit_document(category_path, parsed_id, edited_content)
                    console.print(
                        f"[green]✓ Updated document: {doc_path}[/green]",
                    )
                except (DocumentNotFoundError, DocumentOperationError) as e:
                    handle_cfs_error(e)
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
                from cfs.documents import parse_document_id_from_string

                try:
                    # Find CFS root
                    cfs_root = core.find_cfs_root()
                except CFSNotFoundError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                try:
                    # Get category path
                    category_path = core.get_category_path(cfs_root, cat)
                except InvalidCategoryError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                # Parse ID (handle both numeric ID and filename)
                try:
                    parsed_id = parse_document_id_from_string(doc_id)
                except InvalidDocumentIDError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                # Find document to show preview
                doc_path = documents.find_document_by_id(category_path, parsed_id)
                if doc_path is None or not doc_path.exists():
                    # Use exception for consistent error handling
                    try:
                        raise DocumentNotFoundError(parsed_id, cat)
                    except DocumentNotFoundError as e:
                        handle_cfs_error(e)
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
                    documents.delete_document(category_path, parsed_id)
                    console.print(
                        f"[green]✓ Deleted document: {doc_path}[/green]",
                    )
                except (DocumentNotFoundError, DocumentOperationError) as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

            @category_app.command("view")
            def view_in_category(
                doc_id: Optional[str] = typer.Argument(
                    None,
                    help="Optional document ID to view full content",
                ),
                incomplete_only: bool = typer.Option(
                    False,
                    "--incomplete-only",
                    "-i",
                    help="Show only incomplete issues",
                ),
            ) -> None:
                """View all documents in this category, or view a specific document by ID."""
                from cfs import documents
                from cfs.documents import (
                    parse_document_id_from_string,
                    get_document_title,
                    find_document_by_id,
                    is_document_incomplete,
                )
                from datetime import datetime

                try:
                    # Find CFS root
                    cfs_root = core.find_cfs_root()
                except CFSNotFoundError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                # Validate category (get_category_path will raise if invalid)
                try:
                    category_path = core.get_category_path(cfs_root, cat)
                except InvalidCategoryError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                # If doc_id is provided, show document content
                if doc_id:
                    # Parse document ID
                    try:
                        parsed_id = parse_document_id_from_string(doc_id)
                    except InvalidDocumentIDError as e:
                        handle_cfs_error(e)
                        raise typer.Abort()

                    # Find document
                    doc_path = find_document_by_id(category_path, parsed_id)
                    if doc_path is None or not doc_path.exists():
                        try:
                            raise DocumentNotFoundError(parsed_id, cat)
                        except DocumentNotFoundError as e:
                            handle_cfs_error(e)
                            raise typer.Abort()

                    # Get document content
                    try:
                        title = get_document_title(doc_path)
                        content = doc_path.read_text(encoding="utf-8")
                    except (OSError, IOError) as e:
                        console.print(f"[red]Error reading document: {e}[/red]")
                        raise typer.Abort()

                    # Display document content
                    console.print()
                    console.print(f"[bold]Document:[/bold] {title}")
                    console.print(f"[dim]Category: {cat}, ID: {parsed_id}[/dim]")
                    console.print()
                    console.print("[bold cyan]--- Document Content ---[/bold cyan]")
                    console.print()
                    console.print(content)
                    console.print()
                    console.print("[bold cyan]--- End Document Content ---[/bold cyan]")
                    return

                # No doc_id provided - show table of all documents
                docs_dict = documents.list_documents(cfs_root, cat)
                doc_list = docs_dict.get(cat, [])

                # Filter to incomplete only if flag is set
                if incomplete_only:
                    doc_list = [doc for doc in doc_list if is_document_incomplete(doc)]

                if not doc_list:
                    if incomplete_only:
                        console.print(
                            f"[yellow]No incomplete documents found in {cat} category[/yellow]"
                        )
                    else:
                        console.print(f"[yellow]No documents found in {cat} category[/yellow]")
                    return

                # Create table
                table_title = f"Documents in {cat}"
                if incomplete_only:
                    table_title += " (Incomplete Only)"
                table = Table(title=table_title, box=box.ROUNDED)
                table.add_column("ID", style="cyan", no_wrap=True)
                table.add_column("Title", style="magenta")
                table.add_column("Size", justify="right", style="green")
                table.add_column("Modified", style="yellow")
                table.add_column("Notes", style="yellow")

                for doc in doc_list:
                    size_kb = doc["size"] / 1024
                    size_str = f"{size_kb:.1f} KB" if size_kb >= 1 else f"{doc['size']} B"
                    modified_time = datetime.fromtimestamp(doc["modified"])
                    modified_str = modified_time.strftime("%Y-%m-%d %H:%M")

                    # Add warning for files that don't conform to naming convention
                    notes = get_document_notes(doc, doc_list)

                    table.add_row(
                        str(doc["id"]),
                        doc["title"],
                        size_str,
                        modified_str,
                        notes,
                    )

                console.print()
                console.print(table)

            @category_app.command("complete")
            def complete_in_category(
                doc_id: str = typer.Argument(..., help="Document ID (numeric or filename)"),
                force: bool = typer.Option(
                    False,
                    "--force",
                    "-y",
                    "--yes",
                    help="Skip confirmation and complete immediately",
                ),
            ) -> None:
                """Mark a document as complete by appending '-done' to filename and adding a comment."""
                from cfs import documents
                from cfs.documents import parse_document_id_from_string, get_document_title

                try:
                    # Find CFS root
                    cfs_root = core.find_cfs_root()
                except CFSNotFoundError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                try:
                    # Get category path
                    category_path = core.get_category_path(cfs_root, cat)
                except InvalidCategoryError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                # Parse ID (handle both numeric ID and filename)
                try:
                    parsed_id = parse_document_id_from_string(doc_id)
                except InvalidDocumentIDError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                # Find document to show preview
                doc_path = documents.find_document_by_id(category_path, parsed_id)
                if doc_path is None or not doc_path.exists():
                    try:
                        raise DocumentNotFoundError(parsed_id, cat)
                    except DocumentNotFoundError as e:
                        handle_cfs_error(e)
                        raise typer.Abort()

                # Get document title for confirmation
                try:
                    title = get_document_title(doc_path)
                except Exception:
                    title = doc_path.stem

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

                # Confirm before completing (unless --force flag is set)
                if not force:
                    console.print(f"[bold]Document:[/bold] {title}")
                    console.print(f"[dim]Category: {cat}, ID: {parsed_id}[/dim]")
                    console.print()
                    if not typer.confirm(
                        f"Mark document {parsed_id} as complete?",
                        default=False,
                    ):
                        console.print("[yellow]Operation cancelled[/yellow]")
                        raise typer.Abort()

                # Complete document
                try:
                    new_path = documents.complete_document(category_path, parsed_id)
                    console.print(
                        f"[green]✓ Completed document: {new_path}[/green]",
                    )
                except (DocumentNotFoundError, DocumentOperationError) as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

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
    incomplete_only: bool = typer.Option(
        False,
        "--incomplete-only",
        "-i",
        help="Show only incomplete issues",
    ),
) -> None:
    """View all documents across all categories or a specific category."""
    from cfs import documents
    from cfs.documents import is_document_incomplete
    from datetime import datetime

    try:
        # Find CFS root
        cfs_root = core.find_cfs_root()
    except CFSNotFoundError as e:
        handle_cfs_error(e)
        raise typer.Abort()

    # Validate category if provided
    if category:
        try:
            core.get_category_path(cfs_root, category)
        except InvalidCategoryError as e:
            handle_cfs_error(e)
            raise typer.Abort()

    # List documents
    docs_dict = documents.list_documents(cfs_root, category)

    # Filter to incomplete only if flag is set
    if incomplete_only:
        for cat in docs_dict:
            docs_dict[cat] = [doc for doc in docs_dict[cat] if is_document_incomplete(doc)]

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
            if incomplete_only:
                console.print(
                    f"[yellow]No incomplete documents found in {category} category[/yellow]",
                )
            else:
                console.print(
                    f"[yellow]No documents found in {category} category[/yellow]",
                )
            return

        table_title = f"Documents in {category}"
        if incomplete_only:
            table_title += " (Incomplete Only)"
        table = Table(title=table_title, box=box.ROUNDED)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="magenta")
        table.add_column("Size", justify="right", style="green")
        table.add_column("Modified", style="yellow")
        table.add_column("Notes", style="yellow")

        for doc in doc_list:
            size_kb = doc["size"] / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb >= 1 else f"{doc['size']} B"
            modified_time = datetime.fromtimestamp(doc["modified"])
            modified_str = modified_time.strftime("%Y-%m-%d %H:%M")

            # Add warning for files that don't conform to naming convention
            notes = get_document_notes(doc, doc_list)

            table.add_row(
                str(doc["id"]),
                doc["title"],
                size_str,
                modified_str,
                notes,
            )

        console.print()
        console.print(table)
    else:
        # All categories view
        # Check if any categories have documents
        has_documents = any(doc_list for doc_list in docs_dict.values())

        if not has_documents:
            if incomplete_only:
                console.print("[yellow]No incomplete documents found[/yellow]")
            else:
                console.print("[yellow]No documents found[/yellow]")
            return

        for cat, doc_list in sorted(docs_dict.items()):
            if not doc_list:
                continue

            category_header = f"[bold cyan]{cat.upper()}[/bold cyan]"
            if incomplete_only:
                category_header += " (Incomplete Only)"
            console.print(f"\n{category_header}")
            table = Table(box=box.SIMPLE)
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Title", style="magenta")
            table.add_column("Size", justify="right", style="green")
            table.add_column("Modified", style="yellow")
            table.add_column("Notes", style="yellow")

            for doc in doc_list:
                size_kb = doc["size"] / 1024
                size_str = f"{size_kb:.1f} KB" if size_kb >= 1 else f"{doc['size']} B"
                modified_time = datetime.fromtimestamp(doc["modified"])
                modified_str = modified_time.strftime("%Y-%m-%d %H:%M")

                # Add warning for files that don't conform to naming convention
                notes = get_document_notes(doc, doc_list)

                table.add_row(
                    str(doc["id"]),
                    doc["title"],
                    size_str,
                    modified_str,
                    notes,
                )

            console.print(table)


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
) -> None:
    """Execute instructions from a document by outputting them as custom instructions text.

    This command reads a document and outputs its content as custom instructions that can be
    given to a Cursor agent. In future versions, this may integrate directly with Cursor agents.

    Examples:
        cfs exec bugs 1          # Execute document with ID 1 in bugs category
        cfs exec bugs next       # Execute the next document in bugs category
        cfs exec bugs --next     # Same as above, using flag
    """
    from cfs.documents import (
        parse_document_id_from_string,
        get_next_document_id,
        get_document_title,
        find_document_by_id,
    )

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

    # Show confirmation (unless --force)
    if not force:
        console.print(f"\n[bold]Document:[/bold] {title}")
        console.print(f"[dim]Category: {category}, ID: {target_doc_id}[/dim]")
        console.print()
        if not typer.confirm(
            "Execute this document? (This will output the instructions text)",
            default=False,
        ):
            console.print("[yellow]Execution cancelled[/yellow]")
            raise typer.Abort()

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


@instructions_app.command("next")
def next_document(
    category: str = typer.Argument(..., help="Category name"),
) -> None:
    """Find and work on the next unresolved issue in a category.

    This command finds the first unresolved document (not marked as DONE) in the
    specified category, shows its title, and asks if you want to work on it.
    If yes, it displays the full content and copies it to the clipboard.

    Examples:
        cfs instructions next bugs    # Work on the next bug
        cfs instructions next features  # Work on the next feature
    """
    from cfs.documents import (
        get_next_unresolved_document_id,
        get_document_title,
        find_document_by_id,
    )

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

    # Find next unresolved document
    target_doc_id = get_next_unresolved_document_id(category_path)
    if target_doc_id is None:
        console.print(
            f"[yellow]All of the issues have been completed in the {category} folder. "
            "Please choose another folder to work on.[/yellow]",
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

    # Get document title
    try:
        title = get_document_title(doc_path)
    except Exception as e:
        console.print(f"[red]Error reading document title: {e}[/red]")
        raise typer.Abort()

    # Show title and ask for confirmation
    console.print()
    console.print(f"[bold]Next issue in {category}:[/bold] {title}")
    console.print(f"[dim]Category: {category}, ID: {target_doc_id}[/dim]")
    console.print()

    if not typer.confirm("Would you like to work on this issue?", default=True):
        console.print("[yellow]Cancelled[/yellow]")
        raise typer.Abort()

    # Get document content
    try:
        content = doc_path.read_text(encoding="utf-8")
    except (OSError, IOError) as e:
        console.print(f"[red]Error reading document: {e}[/red]")
        raise typer.Abort()

    # Display full document content
    console.print()
    console.print("[bold cyan]--- Document Content ---[/bold cyan]")
    console.print()
    console.print(content)
    console.print()
    console.print("[bold cyan]--- End Document Content ---[/bold cyan]")
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


@handoff_app.callback(invoke_without_command=True)
def handoff_callback(ctx: typer.Context) -> None:
    """Generate instructions for creating a handoff document."""
    if ctx.invoked_subcommand is None:
        create_handoff()


@handoff_app.command("create-handoff")
def create_handoff() -> None:
    """Generate instructions for creating a handoff document.

    This command prints instructions that you can paste into a Cursor agent
    to create a detailed handoff document. The instructions are automatically
    copied to your clipboard.

    The handoff document will be saved in the progress folder and can be
    picked up by a new agent using 'cfs instructions handoff pickup'.
    """
    try:
        # Find CFS root
        cfs_root = core.find_cfs_root()
    except CFSNotFoundError as e:
        handle_cfs_error(e)
        raise typer.Abort()

    # Get repository root (parent of .cursor directory)
    repo_root = cfs_root.parent

    # Format the repository path for display (use ~ for home directory if applicable)
    try:
        repo_path_str = str(repo_root.resolve())
        home_dir = Path.home()
        if repo_path_str.startswith(str(home_dir)):
            repo_path_str = "~" + repo_path_str[len(str(home_dir)) :]
    except Exception:
        repo_path_str = str(repo_root)

    # Generate handoff instructions
    handoff_instructions = f"""# Create Handoff Document

Please create a comprehensive handoff document that summarizes the current state of the work I've been doing. This document will help a new agent (or me later) pick up where we left off.

## Working directory

`{repo_path_str}`

## Instructions

Create a detailed handoff document using the CFS CLI. Run this command to create the document with proper naming:

```bash
cfs instructions progress create --title "handoff-{{descriptive-title}}"
```

For example:
```bash
cfs instructions progress create --title "handoff-feature-implementation-phase-2"
```

This will create a document like `3-handoff-feature-implementation-phase-2.md` in the `.cursor/progress/` folder with the correct ID.

## Document Content

The handoff document should include:

1. **Project Overview**: Brief description of what we're working on
2. **Current State**: What has been completed so far
3. **In Progress**: What is currently being worked on
4. **Next Steps**: What needs to be done next
5. **Key Implementation Details**: Important technical details, patterns, or decisions
6. **Project Structure**: Overview of the codebase structure
7. **Known Issues**: Any problems or blockers encountered
8. **Questions for Next Agent**: Any questions or decisions that need to be made
9. **Resources**: Links to relevant documentation, files, or resources

## Document Format

- Use Markdown format
- Be comprehensive but organized
- Include code examples or snippets where relevant
- Document any important context or decisions
- Use clear headings and sections

## After Creation

Once created, a new agent can pick up this handoff document by running:
```bash
cfs instructions handoff pickup
```
"""

    # Display instructions
    console.print()
    console.print("[bold cyan]--- Handoff Instructions ---[/bold cyan]")
    console.print()
    console.print(handoff_instructions)
    console.print()
    console.print("[bold cyan]--- End Handoff Instructions ---[/bold cyan]")
    console.print()

    # Copy to clipboard
    try:
        import pyperclip

        pyperclip.copy(handoff_instructions)
        console.print("[green]✓ Instructions copied to clipboard[/green]")
        console.print(
            "[dim]Paste these instructions into your Cursor agent to create a handoff document.[/dim]",
        )
    except ImportError:
        console.print(
            "[yellow]⚠️  pyperclip not available - cannot copy to clipboard automatically[/yellow]",
        )
        console.print(
            "[dim]Copy the instructions above and paste them into your Cursor agent.[/dim]",
        )
    except Exception as e:
        console.print(
            f"[yellow]⚠️  Could not copy to clipboard: {e}[/yellow]",
        )
        console.print(
            "[dim]Copy the instructions above and paste them into your Cursor agent.[/dim]",
        )


@handoff_app.command("pickup")
def pickup_handoff() -> None:
    """Pick up the first incomplete handoff document from the progress folder.

    This command finds the first unresolved handoff document (not marked as DONE)
    in the progress folder, shows its title, and asks if you want to work on it.
    If yes, it displays the full content and copies it to the clipboard.

    Examples:
        cfs instructions handoff pickup    # Pick up the next handoff document
    """
    from cfs.documents import (
        get_next_unresolved_document_id,
        get_document_title,
        find_document_by_id,
    )

    try:
        # Find CFS root
        cfs_root = core.find_cfs_root()
    except CFSNotFoundError as e:
        handle_cfs_error(e)
        raise typer.Abort()

    # Get progress category path
    try:
        category_path = core.get_category_path(cfs_root, "progress")
    except InvalidCategoryError as e:
        handle_cfs_error(e)
        raise typer.Abort()

    # Find next unresolved handoff document
    target_doc_id = get_next_unresolved_document_id(category_path)
    if target_doc_id is None:
        console.print(
            "[yellow]No incomplete handoff documents found in the progress folder. "
            "All handoff documents have been completed.[/yellow]",
        )
        raise typer.Abort()

    # Find document
    doc_path = find_document_by_id(category_path, target_doc_id)
    if doc_path is None or not doc_path.exists():
        try:
            raise DocumentNotFoundError(target_doc_id, "progress")
        except DocumentNotFoundError as e:
            handle_cfs_error(e)
            raise typer.Abort()

    # Get document title
    try:
        title = get_document_title(doc_path)
    except Exception as e:
        console.print(f"[red]Error reading document title: {e}[/red]")
        raise typer.Abort()

    # Show title and ask for confirmation
    console.print()
    console.print(f"[bold]Next handoff document:[/bold] {title}")
    console.print(f"[dim]Category: progress, ID: {target_doc_id}[/dim]")
    console.print()

    if not typer.confirm("Would you like to pick up this handoff document?", default=True):
        console.print("[yellow]Cancelled[/yellow]")
        raise typer.Abort()

    # Get document content
    try:
        content = doc_path.read_text(encoding="utf-8")
    except (OSError, IOError) as e:
        console.print(f"[red]Error reading document: {e}[/red]")
        raise typer.Abort()

    # Display full document content
    console.print()
    console.print("[bold cyan]--- Handoff Document Content ---[/bold cyan]")
    console.print()
    console.print(content)
    console.print()
    console.print("[bold cyan]--- End Handoff Document Content ---[/bold cyan]")
    console.print()

    # Copy to clipboard
    try:
        import pyperclip

        pyperclip.copy(content)
        console.print("[green]✓ Handoff document copied to clipboard[/green]")
    except ImportError:
        console.print(
            "[yellow]⚠️  pyperclip not available - cannot copy to clipboard automatically[/yellow]",
        )
        console.print(
            "[dim]Copy the handoff document above and provide it to your Cursor agent.[/dim]",
        )
    except Exception as e:
        console.print(
            f"[yellow]⚠️  Could not copy to clipboard: {e}[/yellow]",
        )
        console.print(
            "[dim]Copy the handoff document above and provide it to your Cursor agent.[/dim]",
        )


@instructions_app.command("order")
def order_documents_command(
    category: str = typer.Argument(..., help="Category name"),
    force: bool = typer.Option(
        False,
        "--force",
        "--yes",
        help="Skip confirmation and rename immediately",
    ),
) -> None:
    """Order documents in a category by renaming them to follow CFS naming convention."""
    from cfs import documents

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

    # Get preview of rename operations (dry run)
    try:
        rename_operations = documents.order_documents(category_path, dry_run=True)
    except DocumentOperationError as e:
        handle_cfs_error(e)
        raise typer.Abort()

    # Check if any changes are needed
    if not rename_operations:
        console.print(
            f"[green]✓ All files in {category} category already follow the naming convention[/green]",
        )
        return

    # Display preview table
    console.print(f"\n[bold]Preview: Renaming files in {category} category[/bold]")
    table = Table(box=box.ROUNDED)
    table.add_column("Current Name", style="cyan")
    table.add_column("New Name", style="green")
    table.add_column("ID", style="yellow", justify="right")

    for op in rename_operations:
        table.add_row(
            op["old_path"].name,
            op["new_path"].name,
            str(op["id"]),
        )

    console.print()
    console.print(table)
    console.print()

    # Confirm before executing (unless --force flag is set)
    if not force:
        if not typer.confirm(
            f"Rename {len(rename_operations)} file(s) in {category} category?",
            default=False,
        ):
            console.print("[yellow]Operation cancelled[/yellow]")
            raise typer.Abort()

    # Execute renames
    try:
        documents.order_documents(category_path, dry_run=False)
        console.print(
            f"[green]✓ Renamed {len(rename_operations)} file(s) in {category} category[/green]",
        )
    except DocumentOperationError as e:
        handle_cfs_error(e)
        raise typer.Abort()


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
        repo_type = _detect_repo_type(cursor_dir)
        language_info = ""
        if repo_type.get("language"):
            language_info = f"\n**Primary Language**: {repo_type['language']}"
            if repo_type.get("framework"):
                language_info += f"\n**Framework**: {repo_type['framework']}"
            if repo_type.get("package_manager"):
                language_info += f"\n**Package Manager**: {repo_type['package_manager']}"

        init_content = f"""# CFS Initialization

This directory was initialized using the Cursor File Structure (CFS) CLI.{language_info}

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

### Quick Start

```bash
# Create a new bug investigation document
cfs instructions bugs create

# Edit a document
cfs instructions bugs edit 1

# View all documents
cfs instructions view

# Create a rules document
cfs rules create
```

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


# Rules commands
@rules_app.command("create")
def create_rule(
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Rule document name (if not provided, will prompt)",
    ),
    edit: bool = typer.Option(
        False,
        "--edit",
        "-e",
        help="Open editor immediately after creating",
    ),
    comprehensive: bool = typer.Option(
        False,
        "--comprehensive",
        "-c",
        help="Create comprehensive base rules document",
    ),
) -> None:
    """Create a new Cursor rules document."""
    from cfs import documents

    try:
        # Find CFS root
        cfs_root = core.find_cfs_root()
    except CFSNotFoundError as e:
        handle_cfs_error(e)
        raise typer.Abort()

    # Get rules directory path
    rules_path = cfs_root / "rules"

    # Check if rules directory is empty (no existing .mdc files)
    existing_rules = list(rules_path.glob("*.mdc")) if rules_path.exists() else []
    is_first_rule = len(existing_rules) == 0

    # If no rules exist and user didn't specify comprehensive, offer it
    if is_first_rule and not comprehensive and name is None:
        console.print(
            "[yellow]No rules files found. This will be your base rules document.[/yellow]",
        )
        comprehensive = typer.confirm(
            "Would you like to create a comprehensive base rules document?",
            default=True,
        )

    # Get name if not provided
    if name is None:
        if comprehensive:
            # Suggest a name based on project
            repo_root = cfs_root.parent
            suggested_name = repo_root.name
            name = typer.prompt(
                "Rule document name (will be converted to kebab-case)",
                default=suggested_name,
            )
        else:
            name = typer.prompt("Rule document name (will be converted to kebab-case)")

        if not name.strip():
            console.print("[red]Error: Name cannot be empty[/red]")
            raise typer.Abort()

    # Convert to kebab-case
    kebab_name = documents.kebab_case(name)

    # Ensure filename ends with .mdc
    if not kebab_name.endswith(".mdc"):
        kebab_name = f"{kebab_name}.mdc"

    file_path = rules_path / kebab_name

    # Check if file already exists
    if file_path.exists():
        console.print(
            f"[yellow]Warning: Rule file '{file_path}' already exists[/yellow]",
        )
        if not typer.confirm("Overwrite existing file?", default=False):
            console.print("[green]Cancelled[/green]")
            raise typer.Abort()

    # Detect repository type for boilerplate
    repo_type = _detect_repo_type(cfs_root)

    # Generate boilerplate content based on repo type and comprehensive flag
    if comprehensive:
        content = _generate_comprehensive_rule_boilerplate(name, repo_type, cfs_root)
    else:
        content = _generate_rule_boilerplate(name, repo_type)

    # If edit flag is set, launch editor with boilerplate
    if edit:
        from cfs import editor

        console.print(f"[yellow]Opening editor for '{kebab_name}'...[/yellow]")
        content = editor.edit_content(content)

    # Create the file
    try:
        rules_path.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        console.print(
            f"[green]✓ Created rule: {file_path}[/green]",
        )
    except Exception as e:
        console.print(f"[red]Error creating rule: {e}[/red]")
        raise typer.Abort()


def _detect_repo_type(cfs_root: Path) -> dict:
    """Detect repository type and technologies.

    Args:
        cfs_root: Path to .cursor directory.

    Returns:
        Dictionary with detected information about repo type.
    """
    repo_root = cfs_root.parent
    detected = {
        "language": None,
        "framework": None,
        "package_manager": None,
        "has_python": False,
        "has_javascript": False,
    }

    # Check for Python
    if (repo_root / "pyproject.toml").exists() or (repo_root / "setup.py").exists():
        detected["language"] = "python"
        detected["has_python"] = True
        detected["package_manager"] = "pip"
        if (repo_root / "poetry.lock").exists():
            detected["package_manager"] = "poetry"
        elif (repo_root / "Pipfile").exists():
            detected["package_manager"] = "pipenv"

    # Check for JavaScript/TypeScript
    if (repo_root / "package.json").exists():
        detected["has_javascript"] = True
        if not detected["language"]:
            detected["language"] = "javascript"
        try:
            import json

            with open(repo_root / "package.json") as f:
                package_data = json.load(f)
                deps = package_data.get("dependencies", {})
                dev_deps = package_data.get("devDependencies", {})

                # Detect frameworks
                if "react" in deps or "react" in dev_deps:
                    detected["framework"] = "react"
                elif "vue" in deps or "vue" in dev_deps:
                    detected["framework"] = "vue"
                elif "next" in deps:
                    detected["framework"] = "nextjs"
                elif "@angular/core" in deps or "@angular/core" in dev_deps:
                    detected["framework"] = "angular"

                if "typescript" in dev_deps or "typescript" in deps:
                    detected["language"] = "typescript"
        except Exception:
            pass

        if (repo_root / "yarn.lock").exists():
            detected["package_manager"] = "yarn"
        elif (repo_root / "pnpm-lock.yaml").exists():
            detected["package_manager"] = "pnpm"
        else:
            detected["package_manager"] = "npm"

    # Check for Ruby/Rails
    if (repo_root / "Gemfile").exists():
        if not detected["language"]:
            detected["language"] = "ruby"
        if (repo_root / "config" / "application.rb").exists():
            detected["framework"] = "rails"

    # Check for Java
    if (repo_root / "pom.xml").exists() or (repo_root / "build.gradle").exists():
        detected["language"] = "java"

    # Check for Go
    if (repo_root / "go.mod").exists():
        detected["language"] = "go"

    return detected


def _generate_rule_boilerplate(name: str, repo_type: dict) -> str:
    """Generate boilerplate content for a rules file.

    Args:
        name: Rule document name.
        repo_type: Dictionary with detected repository information.

    Returns:
        Boilerplate content as string.
    """
    # Determine globs pattern based on language
    globs = "*"
    if repo_type.get("language") == "python":
        globs = "*.py"
    elif repo_type.get("language") == "javascript":
        globs = "*.js"
    elif repo_type.get("language") == "typescript":
        globs = "*.{ts,tsx}"
    elif repo_type.get("language") == "ruby":
        globs = "*.rb"
    elif repo_type.get("language") == "java":
        globs = "*.java"
    elif repo_type.get("language") == "go":
        globs = "*.go"

    # Build description
    desc_parts = [name]
    if repo_type.get("framework"):
        desc_parts.append(f"{repo_type['framework']} framework")
    if repo_type.get("language"):
        desc_parts.append(f"{repo_type['language']} coding standards")
    description = " - ".join(desc_parts)

    # Build content sections
    sections = []

    # Title
    title = name.replace("-", " ").title()
    sections.append(f"# {title}")

    if repo_type.get("language"):
        sections.append(
            "\nThis document provides Cursor AI with coding standards and best practices for this project."
        )
        sections.append("\n## Project Overview")
        sections.append(
            f"\n{name.replace('-', ' ').title()} project using {repo_type['language']}."
        )
        if repo_type.get("framework"):
            sections.append(f"\n**Framework**: {repo_type['framework']}")
        if repo_type.get("package_manager"):
            sections.append(f"\n**Package Manager**: {repo_type['package_manager']}")
    else:
        sections.append(
            f"\nThis document provides Cursor AI with coding standards and best practices for {name.replace('-', ' ')}."
        )

    sections.append("\n## Code Standards")
    sections.append("\n<!-- Add your coding standards here -->")

    sections.append("\n## Best Practices")
    sections.append("\n<!-- Add best practices here -->")

    # Combine into frontmatter + content
    frontmatter = f"""---
globs: {globs}
description: {description}
---
"""

    content = "\n".join(sections)

    return frontmatter + content


def _generate_comprehensive_rule_boilerplate(name: str, repo_type: dict, cfs_root: Path) -> str:
    """Generate comprehensive boilerplate content for a base rules file.

    Args:
        name: Rule document name.
        repo_type: Dictionary with detected repository information.
        cfs_root: Path to .cursor directory.

    Returns:
        Comprehensive boilerplate content as string.
    """
    repo_root = cfs_root.parent

    # Determine globs pattern based on language
    globs = "*"
    if repo_type.get("language") == "python":
        globs = "*.py"
    elif repo_type.get("language") == "javascript":
        globs = "*.js"
    elif repo_type.get("language") == "typescript":
        globs = "*.{ts,tsx}"
    elif repo_type.get("language") == "ruby":
        globs = "*.rb"
    elif repo_type.get("language") == "java":
        globs = "*.java"
    elif repo_type.get("language") == "go":
        globs = "*.go"

    # Build description
    desc_parts = [name.replace("-", " ").title()]
    if repo_type.get("framework"):
        desc_parts.append(f"{repo_type['framework']} framework")
    if repo_type.get("language"):
        desc_parts.append(f"{repo_type['language']} coding standards")
    description = " - ".join(desc_parts)

    # Build comprehensive content sections
    title = name.replace("-", " ").title()

    sections = [f"# {title}"]

    # Project Overview
    if repo_type.get("language"):
        sections.append(
            f"\nThis document provides Cursor AI with specific guidance for working with the {title} codebase"
        )
        if repo_type.get("framework"):
            sections.append(
                f"- a {repo_type['language']} project using {repo_type['framework']} framework."
            )
        else:
            sections.append(f"- a {repo_type['language']} project.")
    else:
        sections.append(
            f"\nThis document provides Cursor AI with coding standards and best practices for {title}."
        )

    sections.append("\n## Technology Stack\n")

    if repo_type.get("language"):
        sections.append(f"- **Language**: {repo_type['language']}")
    if repo_type.get("framework"):
        sections.append(f"- **Framework**: {repo_type['framework']}")
    if repo_type.get("package_manager"):
        sections.append(f"- **Package Manager**: {repo_type['package_manager']}")

    # Detect common tools based on language
    if repo_type.get("language") == "python":
        sections.append("- **Testing**: pytest")
        sections.append("- **Code Quality**: Black (formatting), Ruff (linting)")
        if (repo_root / "pyproject.toml").exists():
            sections.append("- **Packaging**: setuptools with pyproject.toml (PEP 518/621)")

    elif repo_type.get("language") == "javascript":
        sections.append("- **Testing**: Jest or Vitest")
        sections.append("- **Code Quality**: ESLint, Prettier")

    elif repo_type.get("language") == "typescript":
        sections.append("- **Language**: TypeScript")
        sections.append("- **Testing**: Jest or Vitest")
        sections.append("- **Code Quality**: ESLint, Prettier")

    elif repo_type.get("framework") == "rails":
        sections.append("- **Testing**: RSpec")
        sections.append("- **Code Quality**: RuboCop")

    # Code Style & Formatting
    sections.append("\n## Code Style & Formatting\n")

    if repo_type.get("language") == "python":
        sections.append("### Line Length & Formatting")
        # Check pyproject.toml for line length
        line_length = 100
        try:
            # Try tomllib (Python 3.11+)
            try:
                import tomllib

                with open(repo_root / "pyproject.toml", "rb") as f:
                    config = tomllib.load(f)
                    if "tool" in config and "black" in config["tool"]:
                        line_length = config["tool"]["black"].get("line-length", 100)
            except ImportError:
                # Fallback to tomli for Python < 3.11
                try:
                    import tomli as tomllib

                    with open(repo_root / "pyproject.toml", "rb") as f:
                        config = tomllib.load(f)
                        if "tool" in config and "black" in config["tool"]:
                            line_length = config["tool"]["black"].get("line-length", 100)
                except ImportError:
                    pass
        except Exception:
            pass

        sections.append(f"- **Line length**: {line_length} characters")
        sections.append("- **Formatter**: Black")
        sections.append("- **Linter**: Ruff")
        sections.append("- Always run `black src/` and `ruff check src/` before committing")
        sections.append("\n### PEP 8 Compliance")
        sections.append("- Follow PEP 8 standards")
        sections.append("- Use 4 spaces for indentation (no tabs)")
        sections.append(
            "- Use consistent naming: `snake_case` for functions/variables, `PascalCase` for classes"
        )

    elif repo_type.get("language") in ["javascript", "typescript"]:
        sections.append("### Code Style")
        sections.append("- Follow project ESLint configuration")
        sections.append("- Use Prettier for formatting")
        sections.append("- Use consistent naming conventions")

    # Type Hints / TypeScript
    if repo_type.get("language") == "python":
        sections.append("\n## Type Hints\n")
        sections.append(
            "**CRITICAL**: Always use type hints for function signatures and return types.\n"
        )
        sections.append("```python")
        sections.append("from pathlib import Path")
        sections.append("from typing import Optional")
        sections.append("")
        sections.append("def example(start_path: Optional[Path] = None) -> Optional[Path]:")
        sections.append('    """Example function with type hints."""')
        sections.append("    ...")
        sections.append("```")
        sections.append("\n- Use `Optional[T]` for nullable types")
        sections.append("- Use `Path` from pathlib instead of `str` for file paths")
        sections.append("- Import types from `typing` module explicitly")

    elif repo_type.get("language") == "typescript":
        sections.append("\n## Type Safety\n")
        sections.append("**CRITICAL**: Always use TypeScript types and interfaces.\n")
        sections.append("- Use explicit types for function parameters and return values")
        sections.append("- Prefer interfaces over type aliases for object shapes")
        sections.append("- Avoid `any` - use `unknown` when type is truly unknown")

    # Documentation Standards
    sections.append("\n## Documentation Standards\n")

    if repo_type.get("language") == "python":
        sections.append("### Docstrings")
        sections.append("All functions must have docstrings following Google/NumPy style:\n")
        sections.append("```python")
        sections.append("def function_name(param: str) -> int:")
        sections.append('    """Short description.')
        sections.append("    ")
        sections.append("    Args:")
        sections.append("        param: Parameter description.")
        sections.append("        ")
        sections.append("    Returns:")
        sections.append("        Return value description.")
        sections.append('    """')
        sections.append("```")

    # Error Handling
    sections.append("\n## Error Handling\n")
    sections.append("### Exception Types")
    if repo_type.get("language") == "python":
        sections.append(
            "- Use specific exception types: `ValueError`, `FileNotFoundError`, `PermissionError`"
        )
        sections.append("- Raise exceptions with descriptive messages")
    sections.append("- Validate inputs early")
    sections.append("- Include context in error messages")

    # Testing Standards
    sections.append("\n## Testing Standards\n")
    if repo_type.get("language") == "python":
        sections.append("### Test Structure")
        sections.append("- Use pytest for testing")
        sections.append("- Use descriptive test function names")
        sections.append("- Include docstrings explaining what the test verifies")
        sections.append("- Mock external dependencies when appropriate")

    # Project Structure
    sections.append("\n## Project Structure\n")
    sections.append("<!-- Describe your project structure here -->")
    sections.append("\n- Keep code organized in logical modules")
    sections.append("- Each module should have a clear, single responsibility")

    # Module Organization
    sections.append("\n## Module Organization\n")
    sections.append("### Imports Order")
    sections.append("1. Standard library imports")
    sections.append("2. Third-party imports")
    sections.append("3. Local application imports")

    # Code Quality Checklist
    sections.append("\n## Code Quality Checklist\n")
    sections.append("Before committing code, ensure:")
    if repo_type.get("language") == "python":
        sections.append("- [ ] All functions have type hints")
        sections.append("- [ ] All functions have docstrings")
        sections.append("- [ ] Code passes `black` formatting check")
        sections.append("- [ ] Code passes `ruff` linting check")
    sections.append("- [ ] Tests are written for new functionality")
    sections.append("- [ ] Error handling is in place")

    # Development Workflow
    sections.append("\n## Development Workflow\n")
    sections.append("1. **Make changes** in source code")
    if repo_type.get("language") == "python":
        sections.append("2. **Run formatters**: `black src/` and `ruff check src/`")
    sections.append("3. **Write tests**")
    sections.append("4. **Run tests**")
    sections.append("5. **Commit** using conventional commits format")

    # Combine into frontmatter + content
    frontmatter = f"""---
globs: {globs}
description: {description}
---
"""

    content = "\n".join(sections)

    return frontmatter + content


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
