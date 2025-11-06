"""Document management operations for CFS."""

from pathlib import Path
from typing import Optional


def get_next_id(category_path: Path) -> int:
    """Get the next available ID for a category.

    Args:
        category_path: Path to the category directory.

    Returns:
        Next available ID (starts at 1).
    """
    if not category_path.exists():
        return 1

    existing_ids = []
    for file in category_path.iterdir():
        if file.is_file() and file.suffix == ".md":
            # Extract ID from filename (format: ID-title.md)
            parts = file.stem.split("-", 1)
            if parts and parts[0].isdigit():
                existing_ids.append(int(parts[0]))

    if not existing_ids:
        return 1

    return max(existing_ids) + 1


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
