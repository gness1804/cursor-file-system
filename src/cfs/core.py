"""Core CFS operations and utilities."""

from pathlib import Path
from typing import Optional


# Valid CFS categories
VALID_CATEGORIES = {
    "rules",
    "research",
    "bugs",
    "features",
    "refactors",
    "docs",
    "progress",
    "qa",
    "tmp",
}


def find_cfs_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find the .cursor directory by walking up from start_path.
    
    Args:
        start_path: Starting directory path. Defaults to current working directory.
        
    Returns:
        Path to .cursor directory if found, None otherwise.
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path).resolve()
    
    current = start_path.resolve()
    
    # Walk up the directory tree
    while current != current.parent:
        cursor_dir = current / ".cursor"
        if cursor_dir.exists() and cursor_dir.is_dir():
            return cursor_dir
        current = current.parent
    
    return None


def get_category_path(cfs_root: Path, category: str) -> Path:
    """Get the path to a specific category directory.
    
    Args:
        cfs_root: Path to the .cursor directory.
        category: Category name.
        
    Returns:
        Path to the category directory.
        
    Raises:
        ValueError: If category is not valid.
    """
    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"Invalid category: {category}. "
            f"Valid categories are: {', '.join(sorted(VALID_CATEGORIES))}"
        )
    
    return cfs_root / category


def validate_category(category: str) -> bool:
    """Check if a category name is valid.
    
    Args:
        category: Category name to validate.
        
    Returns:
        True if valid, False otherwise.
    """
    return category in VALID_CATEGORIES

