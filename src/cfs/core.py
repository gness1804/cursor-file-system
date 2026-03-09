"""Core CFS operations and utilities."""

import json
import re
from pathlib import Path
from typing import Optional, Set

from cfs.exceptions import CFSNotFoundError, InvalidCategoryError


# Built-in CFS categories
BUILTIN_CATEGORIES = {
    "rules",
    "research",
    "bugs",
    "features",
    "refactors",
    "docs",
    "progress",
    "qa",
    "security",
    "tmp",
}

# Backward-compatible alias used throughout the codebase.
# This intentionally only includes built-ins; custom categories are discovered per-repo.
VALID_CATEGORIES = BUILTIN_CATEGORIES

DEFAULT_HIDDEN_CATEGORIES = {"tmp", "security"}
_CUSTOM_CATEGORY_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_CATEGORY_CONFIG_FILE = ".cfs-categories.json"


def find_cfs_root(start_path: Optional[Path] = None) -> Path:
    """Find the .cursor directory by walking up from start_path.

    Args:
        start_path: Starting directory path. Defaults to current working directory.

    Returns:
        Path to .cursor directory if found.

    Raises:
        CFSNotFoundError: If .cursor directory is not found.
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

    # Not found - provide helpful error message
    current_dir = Path.cwd()
    raise CFSNotFoundError(
        f"CFS structure not found. No .cursor directory found starting from {current_dir}.\n"
        "Run 'cfs init' to initialize CFS structure in the current directory."
    )


def _read_category_config(cfs_root: Path) -> dict:
    """Read per-repo category config from .cursor/.cfs-categories.json."""
    config_path = cfs_root / _CATEGORY_CONFIG_FILE
    if not config_path.exists():
        return {}

    try:
        content = config_path.read_text(encoding="utf-8").strip()
        if not content:
            return {}
        data = json.loads(content)
        if isinstance(data, dict):
            return data
    except (OSError, ValueError, json.JSONDecodeError):
        pass

    return {}


def _write_category_config(cfs_root: Path, config: dict) -> None:
    """Write per-repo category config to .cursor/.cfs-categories.json."""
    config_path = cfs_root / _CATEGORY_CONFIG_FILE
    serialized = json.dumps(config, indent=2, sort_keys=True) + "\n"
    config_path.write_text(serialized, encoding="utf-8")


def get_custom_categories(cfs_root: Path) -> Set[str]:
    """Get all custom categories present as directories under .cursor."""
    if not cfs_root.exists() or not cfs_root.is_dir():
        return set()

    categories = set()
    for entry in cfs_root.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        if entry.name in BUILTIN_CATEGORIES:
            continue
        categories.add(entry.name)
    return categories


def get_all_categories(cfs_root: Path) -> Set[str]:
    """Get all available categories (built-in + custom) for a repo."""
    return set(BUILTIN_CATEGORIES) | get_custom_categories(cfs_root)


def get_hidden_categories(cfs_root: Path) -> Set[str]:
    """Get hidden categories for this repo (default hidden + configured hidden)."""
    hidden = set(DEFAULT_HIDDEN_CATEGORIES)
    config = _read_category_config(cfs_root)
    configured = config.get("hidden_categories", [])
    if isinstance(configured, list):
        hidden |= {str(category) for category in configured if isinstance(category, str)}
    return hidden


def set_category_hidden(cfs_root: Path, category: str, hidden: bool) -> None:
    """Set hidden state for a category in this repo config."""
    config = _read_category_config(cfs_root)
    current = config.get("hidden_categories", [])
    hidden_categories = {str(cat) for cat in current if isinstance(cat, str)}

    if hidden:
        hidden_categories.add(category)
    else:
        hidden_categories.discard(category)

    config["hidden_categories"] = sorted(hidden_categories)
    _write_category_config(cfs_root, config)


def is_valid_custom_category_name(category: str) -> bool:
    """Validate custom category naming rules."""
    return bool(_CUSTOM_CATEGORY_NAME_RE.fullmatch(category))


def create_custom_category(cfs_root: Path, category: str, hidden: bool = False) -> Path:
    """Create a custom category directory under .cursor and optionally hide it from sync."""
    normalized = category.strip()
    if not normalized:
        raise ValueError("Category name cannot be empty")
    if normalized in BUILTIN_CATEGORIES:
        raise ValueError(f"'{normalized}' is already a built-in category")
    if not is_valid_custom_category_name(normalized):
        raise ValueError(
            "Category name must be lowercase letters/numbers with optional hyphens "
            "(example: work, planning-notes)"
        )

    category_path = cfs_root / normalized
    category_path.mkdir(parents=True, exist_ok=True)
    set_category_hidden(cfs_root, normalized, hidden)
    return category_path


def categories_for_command_registration(start_path: Optional[Path] = None) -> Set[str]:
    """Get categories to register as CLI command groups for this runtime."""
    try:
        cfs_root = find_cfs_root(start_path)
        return get_all_categories(cfs_root)
    except CFSNotFoundError:
        return set(BUILTIN_CATEGORIES)


def get_category_path(cfs_root: Path, category: str) -> Path:
    """Get the path to a specific category directory.

    Args:
        cfs_root: Path to the .cursor directory.
        category: Category name.

    Returns:
        Path to the category directory.

    Raises:
        InvalidCategoryError: If category is not valid.
    """
    valid_categories = get_all_categories(cfs_root)
    if category not in valid_categories:
        raise InvalidCategoryError(category, valid_categories)

    return cfs_root / category


def validate_category(category: str, cfs_root: Optional[Path] = None) -> bool:
    """Check if a category name is valid.

    Args:
        category: Category name to validate.

    Returns:
        True if valid, False otherwise.
    """
    if cfs_root is None:
        return category in BUILTIN_CATEGORIES
    return category in get_all_categories(cfs_root)
