"""Shared helper functions for the CFS CLI."""

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
