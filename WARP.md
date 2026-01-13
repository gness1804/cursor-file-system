# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**cursor-instructions-cli** (CFS - Cursor File Structure CLI) is a Python CLI tool for managing Cursor instruction documents within an opinionated file structure framework. It provides a GitHub CLI-like interface for creating, editing, viewing, and managing Cursor instruction documents organized by category (bugs, features, research, refactors, docs, progress, qa, tmp, rules).

The tool enables developers to organize work for Cursor AI agents across different project stages by structuring documents in a standardized `.cursor/` directory.

## Build, Test, and Development Commands

### Installation

```bash
# Development installation (installs package in editable mode with dev dependencies)
pip install -e ".[dev]"

# Production installation
pip install .
```

### Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_cli.py -v

# Run with coverage report
pytest --cov=src/cfs --cov-report=html

# Run a single test
pytest tests/test_cli.py::TestCLI::test_init -v
```

### Code Quality

```bash
# Format code with black
black src/ tests/

# Lint with ruff
ruff check src/ tests/

# Auto-fix ruff issues
ruff check --fix src/ tests/

# Check both formatting and linting (without fixes)
black --check src/ tests/ && ruff check src/ tests/
```

### Version Management

```bash
# Bump patch version (0.1.0 → 0.1.1)
bump2version patch

# Bump minor version (0.1.0 → 0.2.0)
bump2version minor

# Bump major version (0.1.0 → 1.0.0)
bump2version major
```

## Project Architecture

### Core Components

The project has a modular architecture with clear separation of concerns:

**cfs.cli** (`src/cfs/cli.py`)
- Main entry point using Typer framework
- Defines CLI command structure: `cfs`, `instructions`/`instr`, `rules`
- Contains error handling with user-friendly messages
- Dynamically creates category subcommands (bugs, features, research, etc.)
- Uses Rich library for formatted output (tables, colors, styling)

**cfs.core** (`src/cfs/core.py`)
- Core business logic for CFS operations
- `find_cfs_root()`: Walks up directory tree to locate `.cursor` directory
- `get_category_path()`: Resolves category directories
- `VALID_CATEGORIES`: Set of allowed category names
- No I/O or editor integration—pure utility functions

**cfs.documents** (`src/cfs/documents.py`)
- Document management: CRUD operations on `.md` files
- `get_next_id()`: Auto-increments document IDs per category
- `parse_document_id()`: Extracts ID from filenames
- `find_document_by_id()`: Locates documents by numeric ID or filename
- `kebab_case()` / `title_case()`: Converts between naming conventions
- `create_document()`: Creates new documents with auto-generated structure

**cfs.editor** (`src/cfs/editor.py`)
- Text editor integration
- `detect_editor()`: Finds available editor via $EDITOR env var or system search
- `edit_content()`: Launches editor with temporary file for editing content

**cfs.exceptions** (`src/cfs/exceptions.py`)
- Custom exception hierarchy: `CFSError` base class with specific subclasses
- Exceptions include context (category, doc_id) for detailed error messages

### Data Flow

1. CLI command parsed by Typer → handler function in cli.py
2. Handler calls `core.find_cfs_root()` to locate `.cursor` directory
3. For document operations, `core.get_category_path()` resolves category
4. `documents` module handles file I/O and naming conventions
5. `editor` module manages editor integration for content editing
6. Errors caught and formatted by `handle_cfs_error()` for display

### Testing Strategy

Tests mirror the source structure:
- `test_cli.py`: Integration tests for CLI commands
- `test_core.py`: Unit tests for CFS discovery and category operations
- `test_documents.py`: Tests for document CRUD operations, ID parsing, naming
- `test_editor.py`: Tests for editor detection and content editing
- `test_exceptions.py`: Tests for exception classes and messages

## Key Design Patterns

**Document ID Management**: Each category maintains independently numbered documents (bugs start at 1, features start at 1, etc.). IDs auto-increment. Documents can be referenced by numeric ID or full filename.

**Auto-Generated Structure**: Documents get auto-generated initial structure with sections for "Working directory", "Contents", and "Acceptance criteria" to standardize documentation.

**CLI Aliases**: `instructions` command has short alias `instr` for convenience. Both resolve to same subcommand group.

**Error Context**: Custom exceptions preserve context (category, doc_id) so errors can provide actionable suggestions to users.

## Configuration and Dependencies

**pyproject.toml** defines:
- Dependencies: `typer>=0.9.0`, `rich>=13.0.0`, `pyperclip>=1.8.2`
- Dev dependencies: `pytest>=7.0.0`, `pytest-cov>=4.0.0`, `black>=23.0.0`, `ruff>=0.1.0`, `bump2version>=1.0.0`
- Black: 100-character line length, Python 3.8+ target
- Ruff: 100-character line length, Python 3.8+ target
- Entry point: `cfs = "cfs.cli:main"`

## Common Development Tasks

### Adding a New Category Command

New category commands are generated dynamically in `cli.py`'s `create_category_commands()` function. Add the category name to `VALID_CATEGORIES` in `core.py` and it automatically gets CLI commands (create, edit, delete, view, complete, order, next).

### Adding a New Global Command

Define the command function in `cli.py` and register it with the appropriate Typer app:
- Global commands: `app.command()`
- Instructions subcommands: `instructions_app.command()`
- Rules subcommands: `rules_app.command()`

### Debugging CLI Commands

Run commands directly with verbose flags:
```bash
python -m cfs.cli --help
```

Or test directly:
```bash
python -c "from cfs import cli; cli.main()" instructions bugs create --title "Test"
```

## Code Style Notes

- Follow PEP 8; enforced by ruff and black with 100-character line limit
- Type hints throughout (Python 3.8+ compatible)
- Rich library used for all user-facing output formatting
- Temporary files use context managers and cleanup
- Path operations use `pathlib.Path` (not string paths)
