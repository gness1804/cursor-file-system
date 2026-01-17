"""Document management operations for CFS."""

from pathlib import Path
from typing import Any, Dict, List, Optional

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


def title_case(kebab_title: str) -> str:
    """Convert a kebab-case string to title case.

    Args:
        kebab_title: Kebab-case string (e.g., "fix-annoying-lag").

    Returns:
        Title case string (e.g., "Fix Annoying Lag").
    """
    # Split by hyphens and capitalize each word
    words = kebab_title.split("-")
    return " ".join(word.capitalize() for word in words if word)


def create_document(
    category_path: Path, title: str, content: str = "", repo_root: Optional[Path] = None
) -> Path:
    """Create a new document with ID prefix.

    Args:
        category_path: Path to the category directory.
        title: Document title (will be converted to kebab-case).
        content: Full document content (including structure). If empty, will generate basic structure.
        repo_root: Path to the repository root (parent of .cursor). Used only if content is empty.

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

    # If content is provided, use it directly (assumes it includes full structure)
    # Otherwise, generate basic structure (for backward compatibility)
    if content:
        document_content = content
    else:
        # Generate document structure (backward compatibility)
        title_case_title = title_case(kebab_title)

        # Get repository root path
        if repo_root is None:
            # Infer from category_path: category_path -> .cursor -> repo_root
            repo_root = category_path.parent.parent

        # Format the repository path for display (use ~ for home directory if applicable)
        try:
            repo_path_str = str(repo_root.resolve())
            home_dir = Path.home()
            if repo_path_str.startswith(str(home_dir)):
                repo_path_str = "~" + repo_path_str[len(str(home_dir)) :]
        except Exception:
            repo_path_str = str(repo_root)

        # Build document content with structure
        document_lines = [
            f"# {title_case_title}",
            "",
            "## Working directory",
            "",
            f"`{repo_path_str}`",
            "",
            "## Contents",
            "",
        ]
        document_content = "\n".join(document_lines)

    # Write content to file
    try:
        file_path.write_text(document_content, encoding="utf-8")
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


def get_next_document_id(category_path: Path) -> Optional[int]:
    """Get the ID of the next (first) document in a category.

    Args:
        category_path: Path to the category directory.

    Returns:
        Document ID of the first document (lowest ID), or None if no documents exist.
    """
    if not category_path.exists():
        return None

    doc_ids = []
    for file in category_path.iterdir():
        if file.is_file() and file.suffix == ".md":
            parsed_id = parse_document_id(file.name)
            if parsed_id is not None:
                doc_ids.append(parsed_id)

    if not doc_ids:
        return None

    return min(doc_ids)


def is_document_incomplete(doc_info: Dict[str, Any]) -> bool:
    """Check if a document is incomplete (not marked as DONE or CLOSED).
    Args:
        doc_info: Document info dict with 'id' and 'path' keys.
    Returns:
        True if document is incomplete, False if completed or closed.
    """
    doc_path = doc_info.get("path")
    doc_id = doc_info.get("id")

    if doc_path is None or doc_id is None:
        return True  # Treat as incomplete if info is missing

    stem = doc_path.stem
    # Completed documents have format: {id}-DONE-{title}
    is_completed = stem.startswith(f"{doc_id}-DONE-")
    # Closed documents have format: {id}-CLOSED-{title}
    is_closed = stem.startswith(f"{doc_id}-CLOSED-")
    return not is_completed and not is_closed


def get_next_unresolved_document_id(category_path: Path) -> Optional[int]:
    """Get the ID of the next (first) unresolved document in a category.
    Unresolved documents are those that don't have 'DONE' or 'CLOSED' in their filename.
    Completed documents have the format: {id}-DONE-{title}.md
    Closed documents have the format: {id}-CLOSED-{title}.md
    Args:
        category_path: Path to the category directory.
    Returns:
        Document ID of the first unresolved document (lowest ID), or None if no unresolved documents exist.
    """
    if not category_path.exists():
        return None

    unresolved_doc_ids = []
    for file in category_path.iterdir():
        if file.is_file() and file.suffix == ".md":
            parsed_id = parse_document_id(file.name)
            if parsed_id is not None:
                # Check if document is completed (has DONE in filename)
                stem = file.stem
                # Completed documents have format: {id}-DONE-{title}
                is_completed = stem.startswith(f"{parsed_id}-DONE-")
                # Closed documents have format: {id}-CLOSED-{title}
                is_closed = stem.startswith(f"{parsed_id}-CLOSED-")
                if not is_completed and not is_closed:
                    unresolved_doc_ids.append(parsed_id)

    if not unresolved_doc_ids:
        return None

    return min(unresolved_doc_ids)


def get_document_title(doc_path: Path) -> str:
    """Extract title from a document.

    First tries to extract from filename, then falls back to first markdown heading.

    Args:
        doc_path: Path to the document file.

    Returns:
        Document title as string.
    """
    # Try to extract from filename first
    parsed_id = parse_document_id(doc_path.name)
    if parsed_id is not None:
        stem = doc_path.stem
        if "-" in stem:
            title = stem.split("-", 1)[1]
            # Convert kebab-case back to title case for display
            title = title.replace("-", " ").title()
            return title

    # Fall back to first markdown heading in content
    try:
        content = doc_path.read_text(encoding="utf-8")
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
            elif line.startswith("## "):
                return line[3:].strip()
    except Exception:
        pass

    # Final fallback: use filename without extension
    return doc_path.stem.replace("-", " ").title()


def order_documents(category_path: Path, dry_run: bool = True) -> List[Dict[str, Any]]:
    """Order documents in a category by renaming them to follow CFS naming convention.

    Args:
        category_path: Path to the category directory.
        dry_run: If True, return rename operations without executing. If False, perform renames.

    Returns:
        List of rename operation dictionaries with keys: 'old_path', 'new_path', 'id', 'title'.

    Raises:
        DocumentOperationError: If there's an issue reading or renaming files.
    """
    if not category_path.exists():
        return []

    # Collect all .md files
    files = []
    try:
        for file_path in category_path.iterdir():
            if file_path.is_file() and file_path.suffix == ".md":
                # Extract title from filename
                parsed_id = parse_document_id(file_path.name)
                stem = file_path.stem

                if parsed_id is not None:
                    # File has ID prefix - extract title after ID
                    title = stem.split("-", 1)[1] if "-" in stem else stem
                else:
                    # File doesn't have ID prefix - use full stem as title
                    title = stem

                files.append(
                    {
                        "path": file_path,
                        "title": title,
                    }
                )
    except (OSError, PermissionError) as e:
        raise DocumentOperationError(
            "order documents",
            f"Cannot read category directory: {e}",
        )

    if not files:
        return []

    # Sort files alphabetically by current filename for consistent ordering
    files.sort(key=lambda x: x["path"].name.lower())

    # Generate rename operations
    rename_operations = []
    used_ids = set()
    next_id = 1

    for file_info in files:
        file_path = file_info["path"]
        title = file_info["title"]

        # Convert title to kebab-case
        kebab_title = kebab_case(title)

        # Find next available ID (handle conflicts)
        while next_id in used_ids:
            next_id += 1

        # Generate new filename
        new_filename = f"{next_id}-{kebab_title}.md" if kebab_title else f"{next_id}.md"
        new_path = category_path / new_filename

        # Check if rename is needed
        if file_path.name != new_filename:
            rename_operations.append(
                {
                    "old_path": file_path,
                    "new_path": new_path,
                    "id": next_id,
                    "title": title,
                }
            )

            # Mark this ID as used
            used_ids.add(next_id)
            next_id += 1
        else:
            # File already has correct name - mark ID as used but don't rename
            used_ids.add(next_id)
            next_id += 1

    # Execute renames if not dry run
    if not dry_run and rename_operations:
        # Handle potential conflicts by using temporary names
        # First, rename all files to temporary names
        temp_renames = []
        for op in rename_operations:
            temp_name = f".tmp_{op['old_path'].name}"
            temp_path = op["old_path"].parent / temp_name
            try:
                op["old_path"].rename(temp_path)
                temp_renames.append((temp_path, op["new_path"]))
            except (OSError, PermissionError) as e:
                # Rollback any temp renames that succeeded
                for temp_file, _ in temp_renames:
                    try:
                        # Try to restore original name
                        original_name = temp_file.name.replace(".tmp_", "")
                        temp_file.rename(temp_file.parent / original_name)
                    except Exception:
                        pass
                raise DocumentOperationError(
                    "order documents",
                    f"Cannot rename file {op['old_path']}: {e}",
                )

        # Then rename from temp names to final names
        for temp_path, final_path in temp_renames:
            try:
                temp_path.rename(final_path)
            except (OSError, PermissionError) as e:
                # Rollback: try to restore original name
                try:
                    original_name = temp_path.name.replace(".tmp_", "")
                    temp_path.rename(temp_path.parent / original_name)
                except Exception:
                    pass
                raise DocumentOperationError(
                    "order documents",
                    f"Cannot rename file to {final_path}: {e}",
                )

    return rename_operations


def complete_document(category_path: Path, doc_id: int) -> Path:
    """Mark a document as complete by inserting 'DONE' after the ID in filename and adding a comment.

    Args:
        category_path: Path to the category directory.
        doc_id: Document ID to complete.

    Returns:
        Path to the completed document file.

    Raises:
        DocumentNotFoundError: If document is not found.
        DocumentOperationError: If file cannot be read, written, or renamed.
    """
    # Find document
    doc_path = find_document_by_id(category_path, doc_id)
    if doc_path is None or not doc_path.exists():
        category_name = category_path.name if category_path.exists() else "unknown"
        raise DocumentNotFoundError(doc_id, category_name)

    stem = doc_path.stem

    # Check if already completed (check for pattern: {id}-DONE-)
    if stem.startswith(f"{doc_id}-DONE-"):
        raise DocumentOperationError(
            "complete document",
            f"Document {doc_id} is already marked as done",
        )

    # Parse the filename to extract the title part after the ID
    # Format: {id}-{title} or {id}-DONE-{title}
    if stem.startswith(f"{doc_id}-"):
        # Extract title part (everything after "{id}-")
        title_part = stem[len(f"{doc_id}-") :]
        # If it already starts with "DONE-", it's already completed
        if title_part.startswith("DONE-"):
            raise DocumentOperationError(
                "complete document",
                f"Document {doc_id} is already marked as done",
            )
    else:
        # Filename doesn't match expected pattern, use the whole stem as title
        title_part = stem

    # Read current content
    try:
        content = doc_path.read_text(encoding="utf-8")
    except (OSError, IOError) as e:
        raise DocumentOperationError("read document", str(e))

    # Append completion comment if not already present
    completion_comment = "<!-- DONE -->"
    # Check if comment already exists (with or without surrounding whitespace)
    if completion_comment not in content:
        # Ensure content ends with at least one newline, then add comment
        content = content.rstrip() + "\n\n" + completion_comment + "\n"

    # Generate new filename with 'DONE' after the ID: {id}-DONE-{title}.md
    new_filename = f"{doc_id}-DONE-{title_part}.md"
    new_path = category_path / new_filename

    # Check if new filename already exists (shouldn't happen, but handle it)
    if new_path.exists() and new_path != doc_path:
        raise DocumentOperationError(
            "complete document",
            f"Target filename already exists: {new_path}",
        )

    # Write content to new file
    try:
        new_path.write_text(content, encoding="utf-8")
    except (OSError, IOError, PermissionError) as e:
        raise DocumentOperationError("write document", str(e))

    # Delete old file if it's different from new file
    if doc_path != new_path:
        try:
            doc_path.unlink()
        except (OSError, PermissionError) as e:
            # If deletion fails, try to clean up the new file
            try:
                new_path.unlink()
            except Exception:
                pass
            raise DocumentOperationError("delete old document", str(e))

    return new_path


def close_document(category_path: Path, doc_id: int) -> Path:
    """Mark a document as closed by inserting 'CLOSED' after the ID in filename and adding a comment.
    Args:
        category_path: Path to the category directory.
        doc_id: Document ID to close.
    Returns:
        Path to the closed document file.
    Raises:
        DocumentNotFoundError: If document is not found.
        DocumentOperationError: If file cannot be read, written, or renamed.
    """
    # Find document
    doc_path = find_document_by_id(category_path, doc_id)
    if doc_path is None or not doc_path.exists():
        category_name = category_path.name if category_path.exists() else "unknown"
        raise DocumentNotFoundError(doc_id, category_name)

    stem = doc_path.stem

    # Check if already closed (check for pattern: {id}-CLOSED-)
    if stem.startswith(f"{doc_id}-CLOSED-"):
        raise DocumentOperationError(
            "close document",
            f"Document {doc_id} is already marked as closed",
        )

    # Parse the filename to extract the title part after the ID
    # Format: {id}-{title} or {id}-CLOSED-{title}
    if stem.startswith(f"{doc_id}-"):
        # Extract title part (everything after "{id}-")
        title_part = stem[len(f"{doc_id}-") :]
        # If it already starts with "CLOSED-", it's already closed
        if title_part.startswith("CLOSED-"):
            raise DocumentOperationError(
                "close document",
                f"Document {doc_id} is already marked as closed",
            )
    else:
        # Filename doesn't match expected pattern, use the whole stem as title
        title_part = stem

    # Read current content
    try:
        content = doc_path.read_text(encoding="utf-8")
    except (OSError, IOError) as e:
        raise DocumentOperationError("read document", str(e))

    # Append completion comment if not already present
    closed_comment = "<!-- CLOSED -->"
    # Check if comment already exists (with or without surrounding whitespace)
    if closed_comment not in content:
        # Ensure content ends with at least one newline, then add comment
        content = content.rstrip() + "\n\n" + closed_comment + "\n"

    # Generate new filename with 'CLOSED' after the ID: {id}-CLOSED-{title}.md
    new_filename = f"{doc_id}-CLOSED-{title_part}.md"
    new_path = category_path / new_filename

    # Check if new filename already exists (shouldn't happen, but handle it)
    if new_path.exists() and new_path != doc_path:
        raise DocumentOperationError(
            "close document",
            f"Target filename already exists: {new_path}",
        )

    # Write content to new file
    try:
        new_path.write_text(content, encoding="utf-8")
    except (OSError, IOError, PermissionError) as e:
        raise DocumentOperationError("write document", str(e))

    # Delete old file if it's different from new file
    if doc_path != new_path:
        try:
            doc_path.unlink()
        except (OSError, PermissionError) as e:
            # If deletion fails, try to clean up the new file
            try:
                new_path.unlink()
            except Exception:
                pass
            raise DocumentOperationError("delete old document", str(e))

    return new_path
