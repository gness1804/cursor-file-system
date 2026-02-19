---
github_issue: 17
---
# GitHub Issues Integration - Handoff Document

## Current State

The GitHub Issues integration feature is **functionally complete** (Phases 1-3 done). The user was about to test it when the session limit was reached.

## Branch

`github-issues-integration`

## What Was Implemented

### Phase 1: Foundation (Complete)
- **`src/cfs/github.py`** - GitHub CLI wrapper using `gh` CLI
  - Functions: `check_gh_installed`, `check_gh_authenticated`, `list_issues`, `get_issue`, `create_issue`, `close_issue`, `update_issue`, `add_labels`, `remove_labels`, `ensure_label_exists`
  - Label helpers: `get_cfs_label_for_category` (returns `cfs:<category>`), `get_category_from_cfs_label`

- **`src/cfs/documents.py`** - Added frontmatter support
  - `parse_frontmatter`, `add_frontmatter`, `remove_frontmatter_key`
  - `get_github_issue_number`, `set_github_issue_number`, `remove_github_issue_link`
  - `extract_document_sections`, `build_github_issue_body`

- **`pyproject.toml`** - Added `pyyaml>=6.0` dependency

### Phase 2: Sync Logic (Complete)
- **`src/cfs/sync.py`** - Bidirectional sync logic
  - `build_sync_plan()` - Compares CFS docs with GitHub issues
  - `execute_sync_plan()` - Executes sync actions
  - `generate_diff()`, `display_diff()` - Git-style conflict resolution
  - Detects: new GitHub issues, new CFS docs, status mismatches, content conflicts

### Phase 3: CLI Commands (Complete)
- **`src/cfs/cli.py`** - Added `gh_app` command group
  - `cfs gh sync [--dry-run]` - Bidirectional sync
  - `cfs gh status` - Show sync overview
  - `cfs gh link CATEGORY ID ISSUE` - Manual linking
  - `cfs gh unlink CATEGORY ID` - Remove links

### Tests Added
- `tests/test_github.py` - 20 tests
- `tests/test_frontmatter.py` - 26 tests
- `tests/test_sync.py` - 26 tests
- Total: 72 new tests, all passing

## Commits Made (on `github-issues-integration` branch)
1. `804fcfd` - feat: Add GitHub integration foundation (Phase 1)
2. `005afd2` - feat: Add sync logic module (Phase 2)
3. `0939ac5` - feat: Add GitHub CLI commands (Phase 3)

## Key Design Decisions

1. **Labels**: Use `cfs:<category>` format (e.g., `cfs:features`, `cfs:bugs`)
2. **Content conflicts**: Git-style merge conflict resolution with diff display
3. **Categories to sync**: All except `tmp`
4. **GitHub issue body**: Contains Contents + Acceptance Criteria sections
5. **Status mapping**: Closed GitHub issue → mark CFS as DONE (not CLOSED)
6. **Frontmatter**: Documents link to GitHub via `github_issue: <number>` in YAML frontmatter

## Issue Being Investigated

User ran `cfs gh sync` and noted it didn't seem to pull down GitHub issues. Investigation showed:
- 13 documents are already linked
- 0 unlinked GitHub issues (all issues already have CFS docs)
- 1 content conflict detected

This appears to be working correctly - all GitHub issues in the repo already have corresponding CFS documents. The initial sync must have already created them.

## Remaining Work (Optional)

### Phase 4: Additional Testing
- Integration tests with real GitHub repo (mocked in current tests)

### Phase 5: Documentation & Polish
- Update README with GitHub integration docs
- Edge case handling improvements

## Files Changed

| File | Status |
|------|--------|
| `src/cfs/github.py` | New |
| `src/cfs/sync.py` | New |
| `src/cfs/documents.py` | Modified (added frontmatter functions) |
| `src/cfs/cli.py` | Modified (added gh command group) |
| `pyproject.toml` | Modified (added pyyaml) |
| `tests/test_github.py` | New |
| `tests/test_frontmatter.py` | New |
| `tests/test_sync.py` | New |
| `CLAUDE.md` | Modified (added acceptance criteria to doc structure) |

## How to Test

```bash
cfs gh status          # See sync overview
cfs gh sync --dry-run  # Preview changes
cfs gh sync            # Run actual sync
```

## Plan Document

Full implementation plan is at `.cursor/progress/5-github-issues-integration-plan.md`

<!-- DONE -->
