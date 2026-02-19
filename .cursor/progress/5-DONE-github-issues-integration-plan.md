---
github_issue: 13
---
# GitHub Issues Integration Plan

## Overview

This document outlines the implementation plan for integrating CFS with GitHub Issues, enabling bidirectional syncing between local CFS documents and remote GitHub issues.

## Architecture Decisions

### Metadata Storage

To link CFS documents to GitHub issues, we need to store metadata. Proposed approach:
- Add an optional YAML frontmatter block to CFS documents containing `github_issue_number`
- Example:
  ```markdown
  ---
  github_issue: 42
  ---
  # Document Title
  ...
  ```
- This approach is non-invasive and keeps metadata alongside content

### GitHub Authentication

- Use the `gh` CLI (GitHub's official CLI) for authentication and API calls
- This avoids storing tokens directly and leverages existing user authentication
- Prerequisite: User must have `gh` CLI installed and authenticated

### Category Mapping

- Use GitHub labels with format `cfs:<category>` (e.g., `cfs:features`, `cfs:bugs`)
- When syncing new GitHub issues to CFS: use label if present, otherwise prompt user for category
- Sync all categories **except `tmp`**

### Content Conflict Resolution

- Treat content differences like Git merge conflicts
- Present a diff to the user showing local (CFS) vs remote (GitHub) versions
- User manually reconciles differences before sync proceeds

### GitHub Issue Body Format

Include both the **Contents** and **Acceptance criteria** sections from the CFS document (these are the two main content sections per `cli.py:229`).

### Status Mapping

- GitHub issues are either **open** or **closed** (no further distinction)
- CFS documents can be **incomplete**, **DONE**, or **CLOSED**
- Closing a GitHub issue → marks CFS document as **DONE**
- Completing/closing a CFS document → closes the GitHub issue

---

## Implementation Steps

### Phase 1: Foundation

#### Step 1.1: Create GitHub Module
- **File**: `src/cfs/github.py`
- **Contents**:
  - Function to check if `gh` CLI is installed and authenticated
  - Function to get repository info (owner/repo) from git remote
  - Function to list GitHub issues (open, closed, all)
  - Function to get a single GitHub issue by number
  - Function to create a GitHub issue
  - Function to close a GitHub issue
  - Function to update a GitHub issue (title, body)
  - Function to add/remove labels on an issue

#### Step 1.2: Add Frontmatter Support to Documents
- **Modify**: `src/cfs/documents.py`
- **Changes**:
  - Add function to parse YAML frontmatter from document content
  - Add function to add/update frontmatter in document
  - Add function to extract `github_issue` number from document
  - Ensure existing document operations preserve frontmatter

#### Step 1.3: Add Dependencies
- **Modify**: `pyproject.toml`
- **Dependencies to add**:
  - `pyyaml>=6.0` for frontmatter parsing (or use regex for minimal dependency)

---

### Phase 2: Sync Logic

#### Step 2.1: Create Sync Module
- **File**: `src/cfs/sync.py`
- **Contents**:
  - Function to compare CFS documents with GitHub issues
  - Function to detect new GitHub issues (not in CFS)
  - Function to detect new CFS documents (not in GitHub)
  - Function to detect status changes (closed in one, open in other)
  - Function to detect content changes (title or body differs)
  - Function to generate and display diffs for content conflicts (using Rich for formatting)

#### Step 2.2: Implement Sync Operations
- **File**: `src/cfs/sync.py` (continued)
- **Operations**:
  - `sync_github_to_cfs()`: Create CFS docs for new GitHub issues
  - `sync_cfs_to_github()`: Create GitHub issues for new CFS docs
  - `sync_status_changes()`: Close/reopen issues to match status
  - `resolve_content_conflicts()`: Present diff to user, allow manual reconciliation (like Git merge conflicts)

---

### Phase 3: CLI Commands

#### Step 3.1: Add `gh` Command Group
- **Modify**: `src/cfs/cli.py`
- **New commands**:
  ```
  cfs gh
  ├── sync [--dry-run] [--direction {both,to-github,to-cfs}]
  ├── status                    # Show sync status overview
  ├── link CATEGORY ID ISSUE    # Manually link CFS doc to GitHub issue
  └── unlink CATEGORY ID        # Remove GitHub link from CFS doc
  ```

#### Step 3.2: Implement `cfs gh sync`
- **Behavior**:
  1. Check `gh` CLI is available and authenticated
  2. Get repository info from git remote
  3. Fetch all GitHub issues (open and closed)
  4. Scan all CFS documents for `github_issue` frontmatter
  5. Build comparison: which docs are linked, which are new
  6. For new GitHub issues:
     - Prompt user for category (unless label provides hint)
     - Create CFS document with frontmatter link
  7. For new CFS documents (no `github_issue`):
     - Create GitHub issue with matching content
     - Add frontmatter link to CFS document
  8. For status mismatches:
     - If CFS is DONE/CLOSED and GitHub is open: close GitHub issue
     - If GitHub is closed and CFS is incomplete: mark CFS as DONE
  9. Display summary of changes made

#### Step 3.3: Implement `cfs gh status`
- **Behavior**:
  - Show count of linked documents
  - Show count of unlinked CFS documents
  - Show count of unlinked GitHub issues
  - Show any status mismatches

#### Step 3.4: Implement `cfs gh link` and `cfs gh unlink`
- **Behavior**:
  - `link`: Add `github_issue` frontmatter to existing CFS document
  - `unlink`: Remove `github_issue` frontmatter from CFS document

---

### Phase 4: Testing

#### Step 4.1: Unit Tests for GitHub Module
- **File**: `tests/test_github.py`
- **Tests**:
  - Test `gh` CLI detection
  - Test repository info extraction
  - Mock tests for GitHub API operations

#### Step 4.2: Unit Tests for Sync Module
- **File**: `tests/test_sync.py`
- **Tests**:
  - Test comparison logic
  - Test sync operations with mocked GitHub responses

#### Step 4.3: Integration Tests
- **File**: `tests/test_github_integration.py`
- **Tests**:
  - End-to-end sync tests (may require test repository)
  - Test with `--dry-run` flag

#### Step 4.4: Update Existing Tests
- Ensure frontmatter changes don't break existing document tests

---

### Phase 5: Documentation and Polish

#### Step 5.1: Update README
- Add section on GitHub integration
- Document prerequisites (`gh` CLI)
- Provide usage examples

#### Step 5.2: Error Handling
- Handle missing `gh` CLI gracefully
- Handle authentication failures
- Handle network errors
- Handle rate limiting

#### Step 5.3: Edge Cases
- Handle documents without titles
- Handle very long issue bodies
- Handle special characters in titles
- Handle deleted issues on either side

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `src/cfs/github.py` | Create | GitHub API wrapper using `gh` CLI |
| `src/cfs/sync.py` | Create | Sync logic between CFS and GitHub |
| `src/cfs/documents.py` | Modify | Add frontmatter support |
| `src/cfs/cli.py` | Modify | Add `gh` command group |
| `pyproject.toml` | Modify | Add pyyaml dependency (if needed) |
| `tests/test_github.py` | Create | GitHub module tests |
| `tests/test_sync.py` | Create | Sync module tests |
| `tests/test_documents.py` | Modify | Add frontmatter tests |

---

## Decisions (Resolved)

| Question | Decision |
|----------|----------|
| Label convention | Use `cfs:<category>` format (e.g., `cfs:features`, `cfs:bugs`) |
| Content conflicts | Treat like Git merge conflicts - present diff, user reconciles |
| Categories to sync | All categories **except `tmp`** |
| GitHub issue body | Include **Contents** and **Acceptance criteria** sections |
| Closed GitHub → CFS | Mark as **DONE** (not CLOSED) |

---

## Next Steps

1. Get final approval on this plan
2. Begin Phase 1 implementation
3. Review after each phase before proceeding

<!-- DONE -->
