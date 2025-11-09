"""Document management operations for CFS."""

from pathlib import Path
from typing import Optional, List, Dict, Any

from cfs.exceptions import DocumentNotFoundError, DocumentOperationError, InvalidDocumentIDError


def get_next_id(category_path: Path) -> int:
    """Get the next available ID for a category.

    Args:
        category_path: Path to the category directory.

    Returns:
        Next available ID (starts at 1).

    Raises:
        DocumentOperationError: If there's an issue reading the directory.
    """
    if not category_path.exists():
        return 1

    existing_ids = []
    try:
        for file in category_path.iterdir():
            if file.is_file() and file.suffix == ".md":
                # Extract ID from filename (format: ID-title.md)
                parts = file.stem.split("-", 1)
                if parts and parts[0].isdigit():
                    existing_ids.append(int(parts[0]))

        if not existing_ids:
            return 1

        # Check for duplicate IDs (edge case)
        if len(existing_ids) != len(set(existing_ids)):
            # Found duplicates - warn but continue
            # This shouldn't happen in normal operation
            import warnings

            warnings.warn(
                f"Duplicate IDs detected in {category_path}. "
                "This may indicate a file system issue.",
                UserWarning,
            )

        return max(existing_ids) + 1
    except (OSError, PermissionError) as e:
        raise DocumentOperationError(
            "get next ID",
            f"Cannot read category directory: {e}",
        )


def parse_document_id_from_string(doc_id: str) -> int:
    """Parse document ID from string (handles both numeric ID and filename).

    Args:
        doc_id: Document ID as string (numeric ID or filename).

    Returns:
        Parsed document ID as integer.

    Raises:
        InvalidDocumentIDError: If doc_id cannot be parsed as a valid ID.
    """
    # First try parsing as filename
    parsed_id = parse_document_id(doc_id)
    if parsed_id is not None:
        return parsed_id

    # Try parsing as numeric ID
    try:
        return int(doc_id)
    except ValueError:
        raise InvalidDocumentIDError(doc_id)


def parse_document_id(filename: str) -> Optional[int]:
    """Parse document ID from filename.

    Args:
        filename: Filename (with or without extension).

    Returns:
        Document ID if found, None otherwise.
    """
    # Remove extension if present
    stem = Path(filename).stem

    # Extract ID from beginning (format: ID-title or ID)
    parts = stem.split("-", 1)
    if parts and parts[0].isdigit():
        return int(parts[0])

    return None


def find_document_by_id(category_path: Path, doc_id: int) -> Optional[Path]:
    """Find a document by its ID.

    Args:
        category_path: Path to the category directory.
        doc_id: Document ID to find.

    Returns:
        Path to the document if found, None otherwise.
    """
    if not category_path.exists():
        return None

    # Try both numeric ID and full filename match
    id_str = str(doc_id)

    for file in category_path.iterdir():
        if file.is_file() and file.suffix == ".md":
            # Check if ID matches
            parsed_id = parse_document_id(file.name)
            if parsed_id == doc_id:
                return file

            # Also check if filename starts with the ID
            if file.stem.startswith(f"{id_str}-") or file.stem == id_str:
                return file

    return None


def kebab_case(title: str) -> str:
    """Convert a title to kebab-case.

    Args:
        title: Title string.

    Returns:
        Kebab-case string.
    """
    # Replace spaces and underscores with hyphens
    import re

    title = re.sub(r"[\s_]+", "-", title.lower())
    # Remove any non-alphanumeric characters except hyphens
    title = re.sub(r"[^a-z0-9-]", "", title)
    # Remove multiple consecutive hyphens
    title = re.sub(r"-+", "-", title)
    # Remove leading/trailing hyphens
    return title.strip("-")


def create_document(category_path: Path, title: str, content: str = "") -> Path:
    """Create a new document with ID prefix.

    Args:
        category_path: Path to the category directory.
        title: Document title (will be converted to kebab-case).
        content: Initial document content. Defaults to empty string.

    Returns:
        Path to the created document file.

    Raises:
        ValueError: If title is empty or invalid.
        DocumentOperationError: If file cannot be created.
    """
    if not title or not title.strip():
        raise ValueError("Document title cannot be empty")

    # Ensure category directory exists
    try:
        category_path.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        raise DocumentOperationError(
            "create document",
            f"Cannot create category directory: {e}",
        )

    # Get next available ID
    doc_id = get_next_id(category_path)

    # Convert title to kebab-case
    kebab_title = kebab_case(title)

    # Create filename: ID-title.md
    filename = f"{doc_id}-{kebab_title}.md" if kebab_title else f"{doc_id}.md"
    file_path = category_path / filename

    # Check for duplicate filename (edge case)
    if file_path.exists():
        # This shouldn't happen with proper ID generation, but handle it
        raise DocumentOperationError(
            "create document",
            f"File already exists: {file_path}. This may indicate a duplicate ID issue.",
        )

    # Write content to file
    try:
        file_path.write_text(content, encoding="utf-8")
        return file_path
    except (OSError, IOError, PermissionError) as e:
        raise DocumentOperationError("create document", str(e))


def get_document(category_path: Path, doc_id: int) -> str:
    """Find and read a document by its ID.

    Args:
        category_path: Path to the category directory.
        doc_id: Document ID to retrieve.

    Returns:
        Document content as string.

    Raises:
        DocumentNotFoundError: If document is not found.
        DocumentOperationError: If file cannot be read.
    """
    doc_path = find_document_by_id(category_path, doc_id)
    if doc_path is None or not doc_path.exists():
        # Try to determine category name for better error message
        category_name = category_path.name if category_path.exists() else "unknown"
        raise DocumentNotFoundError(doc_id, category_name)

    try:
        return doc_path.read_text(encoding="utf-8")
    except (OSError, IOError) as e:
        raise DocumentOperationError("read document", str(e))


def edit_document(category_path: Path, doc_id: int, content: str) -> Path:
    """Update document content.

    Args:
        category_path: Path to the category directory.
        doc_id: Document ID to update.
        content: New document content.

    Returns:
        Path to the updated document file.

    Raises:
        DocumentNotFoundError: If document is not found.
        DocumentOperationError: If file cannot be written.
    """
    doc_path = find_document_by_id(category_path, doc_id)
    if doc_path is None or not doc_path.exists():
        category_name = category_path.name if category_path.exists() else "unknown"
        raise DocumentNotFoundError(doc_id, category_name)

    try:
        doc_path.write_text(content, encoding="utf-8")
        return doc_path
    except (OSError, IOError, PermissionError) as e:
        raise DocumentOperationError("update document", str(e))


def delete_document(category_path: Path, doc_id: int) -> None:
    """Delete a document by its ID.

    Args:
        category_path: Path to the category directory.
        doc_id: Document ID to delete.

    Raises:
        DocumentNotFoundError: If document is not found.
        DocumentOperationError: If file cannot be deleted.
    """
    doc_path = find_document_by_id(category_path, doc_id)
    if doc_path is None or not doc_path.exists():
        category_name = category_path.name if category_path.exists() else "unknown"
        raise DocumentNotFoundError(doc_id, category_name)

    try:
        doc_path.unlink()
    except (OSError, PermissionError) as e:
        raise DocumentOperationError("delete document", str(e))


def list_documents(
    cfs_root: Path, category: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """List documents in CFS structure.

    Args:
        cfs_root: Path to the .cursor directory.
        category: Optional category name to filter by. If None, lists all categories.

    Returns:
        Dictionary mapping category names to lists of document info dicts.
        Each document dict contains: 'id', 'title', 'path', 'size', 'modified'.

    Example:
        {
            'bugs': [
                {'id': 1, 'title': 'fix-login-bug', 'path': Path(...), ...},
                ...
            ],
            ...
        }
    """
    from cfs.core import VALID_CATEGORIES, get_category_path

    documents: Dict[str, List[Dict[str, Any]]] = {}

    # Determine which categories to list
    categories_to_list = [category] if category else VALID_CATEGORIES

    for cat in categories_to_list:
        if cat not in VALID_CATEGORIES:
            continue

        category_path = get_category_path(cfs_root, cat)
        if not category_path.exists():
            documents[cat] = []
            continue

        # List documents in this category
        doc_list = []
        for file_path in sorted(category_path.iterdir()):
            if file_path.is_file() and file_path.suffix == ".md":
                # Parse ID and title from filename
                parsed_id = parse_document_id(file_path.name)
                conforms_to_naming = parsed_id is not None

                # Handle files with or without ID prefix
                if parsed_id is not None:
                    # Extract title from filename (after ID- prefix)
                    stem = file_path.stem
                    title = stem.split("-", 1)[1] if "-" in stem else stem
                else:
                    # File doesn't have ID prefix - use 0 as ID and full stem as title
                    # This handles legacy files or manually created files
                    parsed_id = 0
                    title = file_path.stem

                # Get file stats
                stat = file_path.stat()

                doc_list.append(
                    {
                        "id": parsed_id,
                        "title": title,
                        "path": file_path,
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "conforms_to_naming": conforms_to_naming,
                    }
                )

        # Sort by ID
        doc_list.sort(key=lambda x: x["id"])
        documents[cat] = doc_list

    return documents
