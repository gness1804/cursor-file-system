# CLAUDE.md - cursor-instructions-cli (CFS)

## Project Overview

CFS (Cursor File Structure CLI) is a Python CLI tool for managing instruction documents within an opinionated `.cursor/` directory structure. Documents are Markdown files organized by category, with status tracked via filename conventions.

## Tech Stack

- **Language**: Python 3.8+
- **CLI Framework**: Typer
- **Terminal Formatting**: Rich (tables, colors, panels)
- **Clipboard**: pyperclip
- **Testing**: pytest
- **Linting/Formatting**: ruff, black (100-char line length)
- **Version Management**: bump2version

## Project Structure

```
src/cfs/
├── cli.py          # Main CLI entry point, all commands defined here
├── core.py         # Core operations (find_cfs_root, VALID_CATEGORIES)
├── documents.py    # Document CRUD operations
├── editor.py       # Text editor integration
└── exceptions.py   # Custom exception hierarchy
```

## Key Concepts

### Document Storage
- Location: `.cursor/{category}/{id}-{kebab-case-title}.md`
- Categories: `rules`, `research`, `bugs`, `features`, `refactors`, `docs`, `progress`, `qa`, `tmp`
- Status markers in filename: `1-title.md` (incomplete), `1-DONE-title.md`, `1-CLOSED-title.md`

### Document Structure
```markdown
# Title

## Working directory

`~/path/to/project`

## Contents

[User content here]

## Acceptance criteria

[Criteria for completion]
```

The skeleton is generated in `cli.py:229` (`initial_content_lines`).

### CLI Command Pattern
Commands are organized under `cfs instructions {category}` (aliases: `instr`, `i`):
- `create`, `edit`, `delete`, `view`, `complete`, `close`

Category commands are generated dynamically in `create_category_commands()` based on `VALID_CATEGORIES`.

## Running Tests

```bash
pytest                    # Run all tests
pytest tests/test_cli.py  # Run specific test file
pytest -v                 # Verbose output
```

## Building/Installing

```bash
pip install -e .          # Install in development mode
pip install -e ".[dev]"   # Include dev dependencies
```

## Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `find_cfs_root()` | core.py | Walks up directory tree to find `.cursor/` |
| `create_document()` | documents.py | Creates new document with auto-generated structure |
| `complete_document()` | documents.py | Marks as DONE (renames file, adds comment) |
| `close_document()` | documents.py | Marks as CLOSED (renames file, adds comment) |
| `find_document_by_id()` | documents.py | Locates document file by numeric ID |
| `get_next_id()` | documents.py | Returns next auto-incrementing ID for category |

## Exception Hierarchy

All exceptions inherit from `CFSError`:
- `CFSNotFoundError` - No `.cursor/` directory found
- `InvalidCategoryError` - Unknown category name
- `DocumentNotFoundError` - Document ID not found
- `InvalidDocumentIDError` - Invalid ID format
- `DocumentOperationError` - File operation failed

## Current Work

GitHub Issues integration is in progress. See `.cursor/progress/5-github-issues-integration-plan.md` for the implementation plan.
