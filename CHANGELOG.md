# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Top-level category commands (#59): the `instructions`/`instr`/`i` prefix is now optional — `cfs bugs complete 7`, `cfs features next`, `cfs handoff pickup`, and `cfs category create <name>` work directly at the top level. The prefixed forms remain permanent, equivalent aliases. Custom categories created at runtime are also available at the top level immediately.
- Reserved top-level names: custom categories can no longer be named `init`, `version`, `tree`, `gh`, `instructions`, `instr`, or `i` (in addition to the command verbs already reserved).

### Changed
- Unified `view` semantics (#59): both `cfs view` and `cfs i view` now show incomplete documents by default; pass `--all`/`-a` to include completed/closed documents. (Previously `cfs i view` showed everything by default; the `-i` flag is still accepted but is now the default behavior.)

### Security
- Category discovery from disk now applies the same guards as category creation (reserved names and kebab-case validation). Previously a crafted directory in an untrusted repo (e.g. a cloned project shipping `.cursor/gh/`) would be registered as a top-level command group and could shadow the real command. Real command groups are also now registered after categories so they win any name collision (defense-in-depth).

## [0.11.0] - 2026-06-11

### Added
- Consistent noun-first command grammar (#16): every category-scoped command now follows `cfs i <category> <verb> [id]`. New canonical forms: `cfs i <category> next`, `cfs i <category> order`, `cfs i <category> move <id> <dest-category>`, `cfs i <category> exec <id>`, and `cfs i handoff create`.
- New built-in `infrastructure-and-deployment` category for infrastructure and deployment-related task documents (peer of `bugs`, `features`, `refactors`, etc.)
- New built-in `ui` category for UI/UX-related task documents (peer of `bugs`, `features`, `refactors`, etc.)

### Deprecated
- Verb-first command forms (#16): `cfs i order <category>`, `cfs i next <category>`, `cfs i move <src> <id> <dest>`, `cfs i view <category>`, and `cfs i handoff create-handoff` still work but are hidden from help, print a deprecation warning, and will be removed in a future version. Bare `cfs i view` (all categories) is unchanged.

## [0.10.1] - 2026-06-01

### Fixed
- Repaired the test suite (bugs/14): reconciled stale `test_documents.py` tests with intended behavior (structured skeleton on empty content; non-conforming `.md` files are listed) and replaced the removed `CliRunner.isolated_filesystem` with a version-independent helper, so `pytest` passes across Typer/Click versions.

## [0.1.0] - 2026-01-09

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
