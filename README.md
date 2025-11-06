# CFS - Cursor File Structure CLI

A command-line tool for managing Cursor instruction documents within an opinionated file structure framework.

## Overview

CFS (Cursor File Structure) CLI enables developers to create, edit, view, and delete Cursor instruction documents in a structured way. These documents help organize work for Cursor AI agents across different stages of a project.

The tool provides a GitHub CLI-like interface for managing instruction documents organized by category (bugs, features, research, etc.), making it easy to track and organize work for AI-assisted development.

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

### Production Installation

```bash
# Install from source
pip install .

# Or install with development dependencies for testing
pip install ".[dev]"
```

After installation, the `cfs` command will be available in your PATH.

## Quick Start

1. **Initialize CFS structure** in your project:
   ```bash
   cfs init
   ```
   This creates a `.cursor` directory with all category folders and an `init.md` file.

2. **Create your first document**:
   ```bash
   cfs instructions bugs create --title "Fix login bug"
   ```

3. **View all documents**:
   ```bash
   cfs instructions view
   ```

## Usage

### Initialization

Initialize a CFS structure in the current directory (or specify a path):

```bash
# Initialize in current directory
cfs init

# Initialize in a specific directory
cfs init --root /path/to/project

# Force reinitialize (preserves existing files)
cfs init --force
```

### Creating Documents

Create new instruction documents in any category:

```bash
# Create with title flag (will prompt to edit)
cfs instructions bugs create --title "Fix login bug"

# Create with title and immediately open editor
cfs instructions bugs create --title "Fix login bug" --edit

# Create with interactive prompts
cfs instructions features create
# Will prompt for: Document title
# Then ask: Would you like to edit now? [y/N]
```

**Example workflow:**
```bash
$ cfs instructions bugs create --title "Fix memory leak in API"
Would you like to edit 'Fix memory leak in API' now? [y/N]: n
✓ Created document: .cursor/bugs/1-fix-memory-leak-in-api.md
```

### Editing Documents

Edit existing documents by ID (numeric or filename):

```bash
# Edit by numeric ID
cfs instructions bugs edit 1

# Edit by full filename
cfs instructions bugs edit 1-fix-login-bug.md
```

The editor will open with the current content. Save and close to update the document.

### Viewing Documents

View documents across all categories or filter by category:

```bash
# View all documents across all categories
cfs instructions view

# View documents in a specific category
cfs instructions bugs view
cfs instructions features view
```

**Example output:**
```
BUGS
┏━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ ID ┃ Title                                ┃ Size ┃ Modified        ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━┩
│ 1  │ Fix login bug                        │ 2.3 KB │ 2024-01-15 10:30 │
│ 2  │ Memory leak in API                   │ 1.8 KB │ 2024-01-15 14:20 │
└━━━━┴━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┴━━━━━━┴━━━━━━━━━━━━━━━━┘
```

### Deleting Documents

Delete documents with confirmation:

```bash
# Delete with confirmation prompt
cfs instructions bugs delete 1

# Delete without confirmation (force)
cfs instructions bugs delete 1 --force
```

**Example:**
```bash
$ cfs instructions bugs delete 1

Document preview:
# Fix login bug
The login functionality is broken...

Are you sure you want to delete document 1? [y/N]: y
✓ Deleted document: .cursor/bugs/1-fix-login-bug.md
```

### Creating Rules Documents

Create Cursor rules documents (`.mdc` files) with automatic boilerplate:

```bash
# Create with name flag
cfs rules create --name "project-rules"

# Create with comprehensive boilerplate
cfs rules create --name "project-rules" --comprehensive

# Create with interactive prompts
cfs rules create
```

The rules command automatically detects your project type (Python, JavaScript, etc.) and generates appropriate boilerplate content.

**Example:**
```bash
$ cfs rules create --name "my-project" --comprehensive
✓ Created rule: .cursor/rules/my-project.mdc
```

The generated file includes:
- Project-specific configuration (language, framework, package manager)
- Code style guidelines
- Type hints/TypeScript standards
- Documentation standards
- Testing guidelines
- Development workflow

## Command Reference

### Global Commands

- `cfs init [--root PATH] [--force]` - Initialize CFS structure
- `cfs version` - Show version number
- `cfs --help` - Show help message

### Instructions Commands

- `cfs instructions <category> create [--title TITLE] [--edit]` - Create new document
- `cfs instructions <category> edit <id>` - Edit existing document
- `cfs instructions <category> delete <id> [--force]` - Delete document
- `cfs instructions <category> view` - View documents in category
- `cfs instructions view [category]` - View all documents or filter by category

### Rules Commands

- `cfs rules create [--name NAME] [--edit] [--comprehensive]` - Create rules document

### Valid Categories

- `bugs` - Bug investigation and fix instructions
- `features` - Feature development documents
- `research` - Research-related documents
- `refactors` - Refactoring-related documents
- `docs` - Documentation creation instructions
- `progress` - Progress tracking and handoff documents
- `qa` - Testing and QA documents
- `tmp` - Temporary files for Cursor agent use
- `rules` - Rules used by Cursor (automatically read by Cursor agents)

## Cursor File Structure (CFS)

The CFS organizes documents into a `.cursor` directory with the following structure:

```
.cursor/
├── init.md                    # CFS initialization info
├── rules/                     # Cursor rules (.mdc files)
│   └── project-rules.mdc
├── bugs/                      # Bug investigation documents
│   ├── 1-fix-login-bug.md
│   └── 2-memory-leak-api.md
├── features/                  # Feature development documents
│   └── 1-add-user-auth.md
├── research/                  # Research documents
├── refactors/                 # Refactoring documents
├── docs/                      # Documentation instructions
├── progress/                  # Progress tracking
├── qa/                        # Testing and QA
└── tmp/                       # Temporary files
```

### Document Naming

Documents are automatically named with an incrementing ID prefix and kebab-case title:
- `1-fix-login-bug.md`
- `2-add-user-authentication.md`
- `3-refactor-api-layer.md`

The ID is auto-incremented per category, so each category starts at 1. You can reference documents by:
- Numeric ID: `cfs instructions bugs edit 1`
- Full filename: `cfs instructions bugs edit 1-fix-login-bug.md`

### Document Format

Instruction documents are Markdown files (`.md`) that can contain:
- Task descriptions
- Implementation steps
- Code examples
- Links and references
- Any Markdown content

Rules documents are Markdown files with frontmatter (`.mdc`) that Cursor automatically reads.

## Examples

### Example Workflow: Bug Fix

```bash
# 1. Initialize CFS (if not already done)
cfs init

# 2. Create a bug document
cfs instructions bugs create --title "Fix login redirect issue"

# 3. Edit the document to add details
cfs instructions bugs edit 1

# 4. View all bugs
cfs instructions bugs view

# 5. After fixing, delete the document
cfs instructions bugs delete 1
```

### Example Workflow: Feature Development

```bash
# Create feature document
cfs instructions features create --title "Add user profile page" --edit

# View all features
cfs instructions features view

# Edit as you work
cfs instructions features edit 1
```

### Example: Setting Up Project Rules

```bash
# Create comprehensive base rules
cfs rules create --name "my-project" --comprehensive --edit

# This generates a rules file with:
# - Project type detection (Python, JavaScript, etc.)
# - Code style guidelines
# - Type hints/TypeScript standards
# - Testing guidelines
# - Development workflow
```

## Development

### Project Structure

```
cursor-instructions-cli/
├── src/
│   └── cfs/
│       ├── __init__.py          # Package init, exports exceptions
│       ├── cli.py               # Main CLI entry point (Typer app)
│       ├── core.py              # Core CFS operations
│       ├── documents.py         # Document CRUD operations
│       ├── editor.py            # Text editor integration
│       └── exceptions.py        # Custom exception classes
├── tests/                       # Test files
│   ├── test_cli.py              # CLI integration tests
│   ├── test_core.py             # Core operations tests
│   ├── test_documents.py       # Document management tests
│   ├── test_editor.py           # Editor integration tests
│   └── test_exceptions.py       # Exception tests
├── pyproject.toml               # Project configuration
└── README.md
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_cli.py -v

# Run with coverage
pytest --cov=src/cfs --cov-report=html
```

### Code Formatting

```bash
# Format code with black
black src/ tests/

# Check code style with ruff
ruff check src/ tests/

# Auto-fix ruff issues
ruff check --fix src/ tests/
```

### Code Quality

The project uses:
- **Black** for code formatting (line length: 100)
- **Ruff** for linting (target Python 3.8+)
- **pytest** for testing
- **Type hints** throughout (Python 3.8+ compatible)

## Troubleshooting

### Issue: "CFS structure not found"

**Solution**: Run `cfs init` in your project root directory. The CFS structure must be initialized before using other commands.

### Issue: "Invalid category" error

**Solution**: Use one of the valid categories: `bugs`, `features`, `research`, `refactors`, `docs`, `progress`, `qa`, `tmp`, or `rules`.

### Issue: Editor doesn't open

**Solution**: Set the `EDITOR` or `VISUAL` environment variable:
```bash
export EDITOR=vim
# or
export EDITOR=nano
# or
export EDITOR=code  # VS Code
```

### Issue: Document not found

**Solution**: Use `cfs instructions <category> view` to list available documents and their IDs.

### Issue: Command not found after installation

**Solution**: Ensure the package is installed and your PATH includes the Python scripts directory:
```bash
pip install -e .
which cfs  # Should show path to cfs command
```

## Roadmap

- **MVP**: CRUD operations for CFS documents
- **v2.0**: GitHub issues integration
- **v3.0**: Cursor Agent CLI integration
- **v4.0+**: MCP integrations, Slack, Discord, etc.

## License

MIT

