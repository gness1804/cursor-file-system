# CFS - Cursor File Structure CLI

A command-line tool for managing Cursor instruction documents within an opinionated file structure framework.

## Overview

CFS (Cursor File Structure) CLI enables developers to create, edit, view, and delete Cursor instruction documents in a structured way. These documents help organize work for Cursor AI agents across different stages of a project.

## Installation

### Development Installation

```bash
# Clone the repository
git clone <repository-url>
cd cursor-instructions-cli

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Usage

After installation, the `cfs` command will be available:

```bash
# Initialize CFS structure in current directory
cfs init

# Create a new bug instruction document
cfs instructions bugs create

# Edit a document by ID
cfs instructions bugs edit 1

# View all documents
cfs instructions view

# View documents in a specific category
cfs instructions research view

# Delete a document
cfs instructions refactors delete 2

# Create a new Cursor rules document
cfs rules create
```

## Cursor File Structure (CFS)

The CFS organizes documents into the following categories:

- **rules/** - Rules used by Cursor (automatically read by Cursor agents)
- **research/** - Research-related documents
- **bugs/** - Bug investigation and fix instructions
- **features/** - Feature development documents
- **refactors/** - Refactoring-related documents
- **docs/** - Documentation creation instructions
- **progress/** - Progress tracking and handoff documents
- **qa/** - Testing and QA documents
- **tmp/** - Temporary files for Cursor agent use

## Document Naming

Documents are automatically named with an incrementing ID prefix:
- `1-fix-login-bug.md`
- `2-add-user-authentication.md`
- `3-refactor-api-layer.md`

## Development

### Project Structure

```
cursor-instructions-cli/
├── src/
│   └── cfs/
│       ├── __init__.py
│       ├── cli.py          # Main CLI entry point
│       ├── core.py          # Core CFS operations
│       ├── documents.py     # Document CRUD operations
│       └── editor.py        # Text editor integration
├── tests/                   # Test files
├── pyproject.toml          # Project configuration
└── README.md
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black src/
ruff check src/
```

## Roadmap

- **MVP**: CRUD operations for CFS documents
- **v2.0**: GitHub issues integration
- **v3.0**: Cursor Agent CLI integration
- **v4.0+**: MCP integrations, Slack, Discord, etc.

## License

MIT

