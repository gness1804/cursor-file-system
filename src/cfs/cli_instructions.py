"""Instructions and category commands for the CFS CLI."""

import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.table import Table

from cfs import core
from cfs.cli_helpers import (
    _try_auto_close_github_issue,
    _try_auto_create_github_issue,
    console,
    get_document_notes,
    handle_cfs_error,
    prompt_editor_selection,
)
from cfs.exceptions import (
    CFSNotFoundError,
    DocumentNotFoundError,
    DocumentOperationError,
    InvalidCategoryError,
    InvalidDocumentIDError,
)

instructions_app = typer.Typer(
    name="instructions",
    help="Manage Cursor instruction documents",
)
handoff_app = typer.Typer(
    name="handoff",
    help="Create and manage handoff documents for agent transitions",
    invoke_without_command=True,
)
instructions_app.add_typer(handoff_app, name="handoff")


# =============================================================================
# Dynamic Category Commands
# =============================================================================


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
                content_body: Optional[str] = typer.Option(
                    None,
                    "--content",
                    "-c",
                    help="Document content (bypasses editor for non-interactive use)",
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

                # Get content - use --content if provided, otherwise prompt/editor
                content = initial_content
                if content_body is not None:
                    # Non-interactive mode: insert content into the Contents section
                    initial_content_lines_with_body = [
                        f"# {title_case_title}",
                        "",
                        "## Working directory",
                        "",
                        f"`{repo_path_str}`",
                        "",
                        "## Contents",
                        "",
                        content_body,
                        "",
                        "## Acceptance criteria",
                        "",
                    ]
                    content = "\n".join(initial_content_lines_with_body)
                elif edit:
                    from cfs import editor

                    console.print(f"[yellow]Opening editor for '{title}'...[/yellow]")
                    content = editor.edit_content(initial_content)
                else:
                    # Prompt user to select an editor
                    editor_choice = prompt_editor_selection(title)
                    if editor_choice is not None:
                        from cfs import editor

                        editor_cmd, editor_args = editor_choice
                        if editor_cmd == "zed":
                            try:
                                doc_path = documents.create_document(
                                    category_path,
                                    title,
                                    initial_content,
                                    repo_root,
                                )
                                console.print(
                                    f"[green]✓ Created document: {doc_path}[/green]",
                                )
                            except (DocumentOperationError, ValueError) as e:
                                if isinstance(e, DocumentOperationError):
                                    handle_cfs_error(e)
                                else:
                                    console.print(f"[red]Error: {e}[/red]")
                                raise typer.Abort()

                            console.print(f"[yellow]Opening {editor_cmd} for '{title}'...[/yellow]")
                            editor.open_file_in_editor(doc_path, editor_cmd, editor_args)
                            _try_auto_create_github_issue(cat, doc_path, title)
                            return

                        console.print(f"[yellow]Opening {editor_cmd} for '{title}'...[/yellow]")
                        content = editor.edit_content(initial_content, editor_cmd, editor_args)

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

                _try_auto_create_github_issue(cat, doc_path, title)

            @category_app.command("edit")
            def edit_in_category(
                doc_id: str = typer.Argument(..., help="Document ID (numeric or filename)"),
                content_body: Optional[str] = typer.Option(
                    None,
                    "--content",
                    "-c",
                    help="New document content (bypasses editor for non-interactive use)",
                ),
            ) -> None:
                """Edit an existing document in this category."""
                from cfs import documents, editor
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

                # Get current content
                try:
                    current_content = documents.get_document(category_path, parsed_id)
                except DocumentNotFoundError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()
                except DocumentOperationError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                if content_body is not None:
                    # Non-interactive mode: use provided content directly
                    try:
                        doc_path = documents.edit_document(category_path, parsed_id, content_body)
                        console.print(
                            f"[green]✓ Updated document: {doc_path}[/green]",
                        )
                    except (DocumentNotFoundError, DocumentOperationError) as e:
                        handle_cfs_error(e)
                        raise typer.Abort()
                    return

                # Get document title for prompt
                from cfs.documents import find_document_by_id, get_document_title

                doc_path = find_document_by_id(category_path, parsed_id)
                if doc_path:
                    try:
                        title = get_document_title(doc_path)
                    except Exception:
                        title = f"Document {parsed_id}"
                else:
                    title = f"Document {parsed_id}"

                # Prompt user to select an editor
                editor_choice = prompt_editor_selection(title)
                if editor_choice is None:
                    console.print("[yellow]Edit cancelled[/yellow]")
                    return

                editor_cmd, editor_args = editor_choice
                if editor_cmd == "zed":
                    if not doc_path:
                        console.print(
                            f"[red]Error: Document with ID {parsed_id} not found[/red]",
                        )
                        raise typer.Abort()
                    console.print(f"[yellow]Opening {editor_cmd} for '{title}'...[/yellow]")
                    editor.open_file_in_editor(doc_path, editor_cmd, editor_args)
                    console.print(
                        f"[green]✓ Opened document: {doc_path}[/green]",
                    )
                    return

                console.print(f"[yellow]Opening {editor_cmd} for '{title}'...[/yellow]")
                edited_content = editor.edit_content(current_content, editor_cmd, editor_args)

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
                from datetime import datetime

                from cfs import documents
                from cfs.documents import (
                    find_document_by_id,
                    get_document_title,
                    is_document_incomplete,
                    parse_document_id_from_string,
                )

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
                from cfs.documents import get_document_title, parse_document_id_from_string

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

                _try_auto_close_github_issue(new_path)

            @category_app.command("uncomplete")
            def uncomplete_in_category(
                doc_id: str = typer.Argument(..., help="Document ID (numeric or filename)"),
                force: bool = typer.Option(
                    False,
                    "--force",
                    "-y",
                    "--yes",
                    help="Skip confirmation and uncomplete immediately",
                ),
            ) -> None:
                """Reverse a document's completion status by removing 'DONE' from filename and content."""
                from cfs import documents
                from cfs.documents import get_document_title, parse_document_id_from_string

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

                # Confirm before uncompleting (unless --force flag is set)
                if not force:
                    console.print(f"[bold]Document:[/bold] {title}")
                    console.print(f"[dim]Category: {cat}, ID: {parsed_id}[/dim]")
                    console.print()
                    if not typer.confirm(
                        f"Remove completion status from document {parsed_id}?",
                        default=False,
                    ):
                        console.print("[yellow]Operation cancelled[/yellow]")
                        raise typer.Abort()

                # Uncomplete document
                try:
                    new_path = documents.uncomplete_document(category_path, parsed_id)
                    console.print(
                        f"[green]✓ Uncompleted document: {new_path}[/green]",
                    )
                except (DocumentNotFoundError, DocumentOperationError) as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

            @category_app.command("unclose")
            def unclose_in_category(
                doc_id: str = typer.Argument(..., help="Document ID (numeric or filename)"),
                force: bool = typer.Option(
                    False,
                    "--force",
                    "-y",
                    "--yes",
                    help="Skip confirmation and unclose immediately",
                ),
            ) -> None:
                """Reverse a document's closed status by removing 'CLOSED' from filename and content."""
                from cfs import documents
                from cfs.documents import get_document_title, parse_document_id_from_string

                try:
                    cfs_root = core.find_cfs_root()
                except CFSNotFoundError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                try:
                    category_path = core.get_category_path(cfs_root, cat)
                except InvalidCategoryError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                try:
                    parsed_id = parse_document_id_from_string(doc_id)
                except InvalidDocumentIDError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                doc_path = documents.find_document_by_id(category_path, parsed_id)
                if doc_path is None or not doc_path.exists():
                    try:
                        raise DocumentNotFoundError(parsed_id, cat)
                    except DocumentNotFoundError as e:
                        handle_cfs_error(e)
                        raise typer.Abort()

                try:
                    title = get_document_title(doc_path)
                except Exception:
                    title = doc_path.stem

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

                if not force:
                    console.print(f"[bold]Document:[/bold] {title}")
                    console.print(f"[dim]Category: {cat}, ID: {parsed_id}[/dim]")
                    console.print()
                    if not typer.confirm(
                        f"Remove closed status from document {parsed_id}?",
                        default=False,
                    ):
                        console.print("[yellow]Operation cancelled[/yellow]")
                        raise typer.Abort()

                try:
                    new_path = documents.unclose_document(category_path, parsed_id)
                    console.print(
                        f"[green]✓ Unclosed document: {new_path}[/green]",
                    )
                except (DocumentNotFoundError, DocumentOperationError) as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

            @category_app.command("close")
            def close_in_category(
                doc_id: str = typer.Argument(..., help="Document ID (numeric or filename)"),
                force: bool = typer.Option(
                    False,
                    "--force",
                    "-y",
                    "--yes",
                    help="Skip confirmation and close immediately",
                ),
            ) -> None:
                """Mark a document as closed by prepending 'CLOSED-' to the filename."""
                from cfs import documents
                from cfs.documents import get_document_title, parse_document_id_from_string

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

                # Confirm before closing (unless --force flag is set)
                if not force:
                    console.print(f"[bold]Document:[/bold] {title}")
                    console.print(f"[dim]Category: {cat}, ID: {parsed_id}[/dim]")
                    console.print()
                    if not typer.confirm(
                        f"Mark document {parsed_id} as closed?",
                        default=False,
                    ):
                        console.print("[yellow]Operation cancelled[/yellow]")
                        raise typer.Abort()

                # close document
                try:
                    new_path = documents.close_document(category_path, parsed_id)
                    console.print(
                        f"[green]✓ Closed document: {new_path}[/green]",
                    )
                except (DocumentNotFoundError, DocumentOperationError) as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                _try_auto_close_github_issue(new_path)

            @category_app.command("check")
            def check_in_category() -> None:
                """Check for duplicate IDs or titles in this category."""
                from cfs.documents import check_duplicates

                try:
                    cfs_root = core.find_cfs_root()
                except CFSNotFoundError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                try:
                    category_path = core.get_category_path(cfs_root, cat)
                except InvalidCategoryError as e:
                    handle_cfs_error(e)
                    raise typer.Abort()

                issues = check_duplicates(category_path)
                if not issues:
                    console.print(f"[green]No duplicate issues found in {cat} category[/green]")
                else:
                    console.print(f"[red]Found {len(issues)} issue(s) in {cat} category:[/red]")
                    for issue in issues:
                        console.print(f"  [yellow]- {issue}[/yellow]")

        # Create all commands for this category
        make_category_commands(category)


# Initialize category commands
create_category_commands()


# =============================================================================
# AI Service Launchers
# =============================================================================


def _launch_claude_code(content: str, category: str, doc_id: int) -> None:
    """Launch Claude Code with document content as the initial prompt.

    Args:
        content: The document content to pass to Claude Code.
        category: The category of the document (for the completion instruction).
        doc_id: The document ID (for the completion instruction).
    """
    # Check if claude command is available
    claude_path = shutil.which("claude")
    if claude_path is None:
        console.print(
            "[red]Error: Claude Code CLI not found. "
            "Please install it from https://claude.ai/code[/red]"
        )
        raise typer.Abort()

    # Build the prompt with the document content and completion instruction
    completion_instruction = (
        f"\n\n---\n\n"
        f"When you are finished with this work, offer to close the corresponding CFS "
        f"document that was passed to you to start this session. The command for this is: "
        f"`cfs i {category} complete {doc_id} --force`"
    )

    prompt = (
        f"Work on the following task from the {category} category (ID: {doc_id}):\n\n"
        f"{content}"
        f"{completion_instruction}"
    )

    console.print("[cyan]Starting Claude Code session...[/cyan]")

    try:
        # Launch Claude Code with the prompt
        subprocess.run([claude_path, prompt], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Claude Code exited with error code {e.returncode}[/red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Claude Code session interrupted[/yellow]")


def _launch_gemini(content: str, category: str, doc_id: int) -> None:
    """Launch Gemini CLI with document content as the initial prompt.

    Args:
        content: The document content to pass to Gemini.
        category: The category of the document (for the completion instruction).
        doc_id: The document ID (for the completion instruction).
    """
    # Check if gemini command is available
    gemini_path = shutil.which("gemini")
    if gemini_path is None:
        console.print(
            "[red]Error: Gemini CLI not found. "
            "Please install it with: npm install -g @google/gemini-cli[/red]"
        )
        raise typer.Abort()

    # Build the prompt with the document content and completion instruction
    completion_instruction = (
        f"\n\n---\n\n"
        f"When you are finished with this work, offer to close the corresponding CFS "
        f"document that was passed to you to start this session. The command for this is: "
        f"`cfs i {category} complete {doc_id} --force`"
    )

    prompt = (
        f"Work on the following task from the {category} category (ID: {doc_id}):\n\n"
        f"{content}"
        f"{completion_instruction}"
    )

    console.print("[cyan]Starting Gemini CLI session...[/cyan]")

    try:
        # Launch Gemini CLI with the prompt
        subprocess.run([gemini_path, prompt], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Gemini CLI exited with error code {e.returncode}[/red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Gemini CLI session interrupted[/yellow]")


def _launch_cursor_agent(content: str, category: str, doc_id: int) -> None:
    """Launch Cursor Agent CLI with document content as the initial prompt.

    Args:
        content: The document content to pass to Cursor Agent.
        category: The category of the document (for the completion instruction).
        doc_id: The document ID (for the completion instruction).
    """
    # Check if agent command is available
    agent_path = shutil.which("agent")
    if agent_path is None:
        console.print(
            "[red]Error: Cursor Agent CLI not found. "
            "Please install it from: https://cursor.com/cli[/red]"
        )
        raise typer.Abort()

    # Build the prompt with the document content and completion instruction
    completion_instruction = (
        f"\n\n---\n\n"
        f"When you are finished with this work, offer to close the corresponding CFS "
        f"document that was passed to you to start this session. The command for this is: "
        f"`cfs i {category} complete {doc_id} --force`"
    )

    prompt = (
        f"Work on the following task from the {category} category (ID: {doc_id}):\n\n"
        f"{content}"
        f"{completion_instruction}"
    )

    console.print("[cyan]Starting Cursor Agent CLI session...[/cyan]")

    try:
        # Launch Cursor Agent CLI with the prompt using 'agent chat'
        subprocess.run([agent_path, "chat", prompt], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Cursor Agent CLI exited with error code {e.returncode}[/red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Cursor Agent CLI session interrupted[/yellow]")


def _launch_codex(content: str, category: str, doc_id: int) -> None:
    """Launch OpenAI Codex CLI with document content as the initial prompt.

    Args:
        content: The document content to pass to Codex.
        category: The category of the document (for the completion instruction).
        doc_id: The document ID (for the completion instruction).
    """
    # Check if codex command is available
    codex_path = shutil.which("codex")
    if codex_path is None:
        console.print(
            "[red]Error: OpenAI Codex CLI not found. "
            "Please install it with: npm install -g @openai/codex[/red]"
        )
        raise typer.Abort()

    # Build the prompt with the document content and completion instruction
    completion_instruction = (
        f"\n\n---\n\n"
        f"When you are finished with this work, offer to close the corresponding CFS "
        f"document that was passed to you to start this session. The command for this is: "
        f"`cfs i {category} complete {doc_id} --force`"
    )

    prompt = (
        f"Work on the following task from the {category} category (ID: {doc_id}):\n\n"
        f"{content}"
        f"{completion_instruction}"
    )

    console.print("[cyan]Starting OpenAI Codex CLI session...[/cyan]")

    try:
        # Launch Codex CLI with the prompt
        subprocess.run([codex_path, prompt], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]OpenAI Codex CLI exited with error code {e.returncode}[/red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]OpenAI Codex CLI session interrupted[/yellow]")


# =============================================================================
# Top-Level Instructions Commands
# =============================================================================


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
    from datetime import datetime

    from cfs import documents
    from cfs.documents import is_document_incomplete

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


@instructions_app.command("next")
def next_document(
    category: str = typer.Argument(..., help="Category name"),
    force: bool = typer.Option(
        False,
        "--force",
        "-y",
        "--yes",
        help="Skip confirmation and work on issue immediately",
    ),
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
        find_document_by_id,
        get_document_title,
        get_next_unresolved_document_id,
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

    if not force:
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


@instructions_app.command("move")
def move_document_command(
    source_category: str = typer.Argument(..., help="Source category name"),
    doc_id: str = typer.Argument(..., help="Document ID (numeric or filename)"),
    dest_category: str = typer.Argument(..., help="Destination category name"),
    no_renumber: bool = typer.Option(
        False,
        "--no-renumber",
        help="Skip renumbering documents in the source category after move",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-y",
        "--yes",
        help="Skip confirmation prompt",
    ),
) -> None:
    """Move a document from one category to another.

    The document receives a new sequential ID in the destination category.
    By default, documents in the source category are renumbered to fill the gap.

    Example: cfs i move features 1 security
    """
    from cfs.documents import (
        find_document_by_id,
        get_document_title,
        move_document,
        parse_document_id_from_string,
    )

    try:
        cfs_root = core.find_cfs_root()
    except CFSNotFoundError as e:
        handle_cfs_error(e)
        raise typer.Abort()

    # Validate source category
    try:
        source_path = core.get_category_path(cfs_root, source_category)
    except InvalidCategoryError as e:
        handle_cfs_error(e)
        raise typer.Abort()

    # Validate destination category
    try:
        dest_path = core.get_category_path(cfs_root, dest_category)
    except InvalidCategoryError as e:
        handle_cfs_error(e)
        raise typer.Abort()

    # Same category check
    if source_category == dest_category:
        console.print("[red]Error: Source and destination categories are the same[/red]")
        raise typer.Abort()

    # Parse document ID
    try:
        parsed_id = parse_document_id_from_string(doc_id)
    except InvalidDocumentIDError as e:
        handle_cfs_error(e)
        raise typer.Abort()

    # Find document to show preview
    doc_path = find_document_by_id(source_path, parsed_id)
    if doc_path is None or not doc_path.exists():
        try:
            raise DocumentNotFoundError(parsed_id, source_category)
        except DocumentNotFoundError as e:
            handle_cfs_error(e)
            raise typer.Abort()

    # Get document title for confirmation
    try:
        title = get_document_title(doc_path)
    except Exception:
        title = doc_path.stem

    # Confirm before moving
    if not force:
        console.print(f"\n[bold]Document:[/bold] {title}")
        console.print(f"[dim]ID: {parsed_id}, Source: {source_category}[/dim]")
        console.print(f"[dim]Destination: {dest_category}[/dim]")
        console.print()
        if not typer.confirm(
            f"Move document {parsed_id} from {source_category} to {dest_category}?",
            default=False,
        ):
            console.print("[yellow]Operation cancelled[/yellow]")
            raise typer.Abort()

    # Move document
    try:
        new_path = move_document(
            source_path,
            dest_path,
            parsed_id,
            renumber=not no_renumber,
        )
        console.print(
            f"[green]✓ Moved document to: {new_path}[/green]",
        )
        if not no_renumber:
            console.print(f"[dim]Documents in {source_category} have been renumbered[/dim]")
    except (DocumentNotFoundError, DocumentOperationError) as e:
        handle_cfs_error(e)
        raise typer.Abort()


# =============================================================================
# Handoff Commands
# =============================================================================


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
def pickup_handoff(
    force: bool = typer.Option(
        False,
        "--force",
        "-y",
        "--yes",
        help="Skip confirmation and pick up handoff immediately",
    ),
) -> None:
    """Pick up the first incomplete handoff document from the progress folder.

    This command finds the first unresolved handoff document (not marked as DONE)
    in the progress folder, shows its title, and asks if you want to work on it.
    If yes, it displays the full content and copies it to the clipboard.

    Examples:
        cfs instructions handoff pickup    # Pick up the next handoff document
    """
    from cfs.documents import (
        find_document_by_id,
        get_document_title,
        get_next_unresolved_document_id,
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

    if not force:
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
