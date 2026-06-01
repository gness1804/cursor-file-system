# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New built-in `infrastructure-and-deployment` category for infrastructure and deployment-related task documents (peer of `bugs`, `features`, `refactors`, etc.)
- New built-in `ui` category for UI/UX-related task documents (peer of `bugs`, `features`, `refactors`, etc.)

## [0.10.1] - 2026-06-01

### Fixed
- Repaired the test suite (bugs/14): reconciled stale `test_documents.py` tests with intended behavior (structured skeleton on empty content; non-conforming `.md` files are listed) and replaced the removed `CliRunner.isolated_filesystem` with a version-independent helper, so `pytest` passes across Typer/Click versions.

## [## [Unreleased]] - 2026-01-09

### Added
- Initial release of cursor-instructions-cli
- Core CLI functionality with Typer framework
- Document CRUD operations (Create, Read, Update, Delete)
- Support for multiple document categories (bugs, features, research, refactors, docs, progress, qa, security, tmp)
- Document completion tracking with DONE prefix
- File tree visualization
- Rules document creation with project type detection
- Handoff document generation and pickup
- Cursor integration via `.cursor` directory structure
- Comprehensive test suite with pytest
- Code quality tools (Black, Ruff)
- Full documentation and usage examples

[Unreleased]: https://github.com/yourusername/cursor-instructions-cli/compare/v## [Unreleased]...HEAD
[## [Unreleased]]: https://github.com/yourusername/cursor-instructions-cli/releases/tag/v## [Unreleased]
