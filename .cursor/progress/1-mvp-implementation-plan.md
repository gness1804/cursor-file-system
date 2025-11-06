# MVP Implementation Plan - CFS CLI

## Project Overview
Build a Python CLI tool (`cfs`) to manage Cursor File Structure (CFS) documents with CRUD operations.

## Technology Stack
- **Language**: Python 3.8+
- **CLI Framework**: Click or Typer (Typer recommended for modern Python)
- **File Operations**: pathlib, os
- **Text Editor Integration**: subprocess for launching editors
- **Configuration**: TOML or YAML for project config
- **Testing**: pytest
- **Packaging**: setuptools, pyproject.toml

## MVP Requirements Summary

### Core Commands
1. `cfs init` - Initialize CFS structure
2. `cfs instructions <category> create` - Create new instruction document
3. `cfs instructions <category> edit <id>` - Edit existing document
4. `cfs instructions <category> delete <id>` - Delete document (with confirmation)
5. `cfs instructions view` - View all documents in CFS
6. `cfs instructions <category> view` - View documents in specific category
7. `cfs rules create` - Create new Cursor rules document

### Categories
- bugs
- features
- refactors
- docs
- research
- progress
- qa
- tmp

## Implementation Steps

### Step 1: Project Setup & Structure ✅ COMPLETE
- [x] Initialize Python project with pyproject.toml
- [x] Set up project directory structure
- [x] Configure dependencies (typer, rich for CLI output, etc.)
- [x] Create basic package structure (`cfs/` directory)
- [x] Set up entry point for `cfs` command
- [x] Create README.md with installation and usage instructions
- [x] Add .gitignore for Python development artifacts

### Step 2: Core CFS Operations Module ✅ COMPLETE
- [x] Create `cfs/core.py` with CFS path detection logic
- [x] Implement function to find `.cursor` directory (walk up from current dir) - `find_cfs_root()`
- [x] Implement function to get next available ID for a category - `get_next_id()` (in documents.py)
- [x] Implement function to parse document ID from filename - `parse_document_id()`
- [x] Implement function to find document by ID in category - `find_document_by_id()`
- [x] Add validation for category names - `validate_category()` and `get_category_path()`

### Step 3: Document Management Module ⚠️ PARTIAL
- [x] Create `cfs/documents.py` with document CRUD operations
- [x] Helper functions implemented: `get_next_id()`, `parse_document_id()`, `find_document_by_id()`, `kebab_case()`
- [ ] Implement `create_document(category, title, content)` - creates file with ID prefix
- [ ] Implement `get_document(category, doc_id)` - finds and reads document
- [ ] Implement `edit_document(category, doc_id, content)` - updates document
- [ ] Implement `delete_document(category, doc_id)` - deletes document with confirmation
- [ ] Implement `list_documents(category=None)` - lists all or category-specific docs

### Step 4: Editor Integration Module ✅ COMPLETE
- [x] Create `cfs/editor.py` for text editor integration
- [x] Implement function to detect available editors (check $EDITOR, then common editors) - `detect_editor()`
- [x] Implement function to launch editor with temporary file - `edit_content()`
- [x] Implement function to capture editor output
- [x] Handle both interactive and non-interactive modes

### Step 5: CLI Commands - Base Structure ⚠️ PARTIAL
- [x] Create `cfs/cli.py` with Typer app setup
- [x] Set up main `cfs` command group
- [x] Basic version command implemented
- [ ] Set up `instructions` subcommand group
- [ ] Set up `rules` subcommand group
- [ ] Add global options (verbose, config path, etc.)

### Step 6: CLI Commands - Init
- [ ] Implement `cfs init` command
- [ ] Create all CFS directories if they don't exist
- [ ] Create `.cursor/init.md` with boilerplate content
- [ ] Handle case where CFS already exists (ask for confirmation or skip)
- [ ] Add option to specify project root vs current directory

### Step 7: CLI Commands - Create
- [ ] Implement `cfs instructions <category> create` command
- [ ] Validate category name
- [ ] Prompt for document title (or accept as argument)
- [ ] Generate next available ID
- [ ] Prompt user: edit now or create empty?
- [ ] If edit now: launch editor, capture content
- [ ] Create document file with ID-title format
- [ ] Show success message with file path

### Step 8: CLI Commands - Edit
- [ ] Implement `cfs instructions <category> edit <id>` command
- [ ] Parse ID (handle both numeric ID and full filename)
- [ ] Find document by ID
- [ ] Load current content
- [ ] Launch editor with current content
- [ ] Save updated content
- [ ] Show success message

### Step 9: CLI Commands - Delete
- [ ] Implement `cfs instructions <category> delete <id>` command
- [ ] Parse ID (handle both numeric ID and full filename)
- [ ] Find document by ID
- [ ] Show document preview (first few lines)
- [ ] Prompt for confirmation
- [ ] Delete file if confirmed
- [ ] Show success message

### Step 10: CLI Commands - View
- [ ] Implement `cfs instructions view` command (all categories)
- [ ] Implement `cfs instructions <category> view` command
- [ ] Format output nicely (tree structure, tables, etc.)
- [ ] Show document IDs, titles, and maybe metadata (date, size)
- [ ] Use rich library for pretty formatting

### Step 11: CLI Commands - Rules
- [ ] Implement `cfs rules create` command
- [ ] Prompt for rules document name/topic
- [ ] Create document in `.cursor/rules/` directory
- [ ] Optionally add boilerplate based on repo type (detect language, framework)

### Step 12: Error Handling & Validation
- [ ] Add error handling for missing CFS structure
- [ ] Add error handling for invalid categories
- [ ] Add error handling for missing documents
- [ ] Add validation for document IDs
- [ ] Add helpful error messages
- [ ] Handle edge cases (empty categories, duplicate IDs, etc.)

### Step 13: Testing
- [ ] Write unit tests for core operations
- [ ] Write unit tests for document management
- [ ] Write integration tests for CLI commands
- [ ] Test editor integration (mock editor calls)
- [ ] Test error cases

### Step 14: Documentation & Polish
- [ ] Complete README.md with examples
- [ ] Add docstrings to all functions
- [ ] Create help text for all commands
- [ ] Add command aliases where useful
- [ ] Create example CFS structure in README
- [ ] Document installation process

### Step 15: Packaging & Distribution
- [ ] Configure `pyproject.toml` for package building
- [ ] Set up entry points for `cfs` command
- [ ] Test installation via pip
- [ ] Create setup instructions
- [ ] Consider publishing to PyPI (future)

## Design Decisions

### ID Generation
- Each category maintains its own ID sequence
- IDs start at 1 and increment
- ID is prepended to filename: `{id}-{kebab-case-title}.md`
- Find next ID by scanning existing files in category

### File Naming
- Format: `{id}-{kebab-case-title}.md`
- Example: `1-fix-login-bug.md`, `2-add-user-authentication.md`
- Title is converted to kebab-case automatically

### Editor Selection Priority
1. `$EDITOR` environment variable
2. Common editors: `vim`, `nano`, `code` (VS Code), `subl` (Sublime)
3. Fallback to `nano` if none found

### CFS Detection
- Walk up directory tree from current directory
- Look for `.cursor` directory
- Stop at filesystem root or Git repo root (configurable)
- Error if not found (with helpful message)

## Next Steps After MVP
- Version 2.0: GitHub integration
- Version 3.0: Cursor Agent CLI integration
- Version 4.0+: MCP integrations, Slack, Discord, etc.

## Questions to Resolve
1. Should `cfs init` be required before other commands, or should commands auto-create missing directories?
2. Should there be a global config file (`~/.cfs/config.toml`) for default editor, etc.?
3. Should document metadata (created date, modified date) be stored in frontmatter or separate metadata file?
4. Should there be a command to rename/move documents (which would require ID renumbering)?

