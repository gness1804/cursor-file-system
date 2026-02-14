"""Cursor File Structure (CFS) CLI tool.

A CLI for managing Cursor instruction documents within a structured file system.
"""

__version__ = "0.8.2"

# Export exceptions for easy access
from cfs.exceptions import (
    CFSError,
    CFSNotFoundError,
    InvalidCategoryError,
    DocumentNotFoundError,
    InvalidDocumentIDError,
    DocumentOperationError,
)

__all__ = [
    "__version__",
    "CFSError",
    "CFSNotFoundError",
    "InvalidCategoryError",
    "DocumentNotFoundError",
    "InvalidDocumentIDError",
    "DocumentOperationError",
]
