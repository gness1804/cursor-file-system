---
github_issue: 61
---
# Gh Sync Conflict Loop Section Parsers Not Code Fence Aware

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

Resolving a content conflict via `cfs gh sync` does not converge for documents whose content contains heading-like lines inside fenced code blocks: the same conflict reappears on every subsequent sync.

Root cause: three parsers treat ANY line starting with `## ` as a section header, even inside ``` code fences:

- `extract_document_sections()` (documents.py)
- `build_github_issue_body()` (uses the above)
- `_split_github_issue_body()` (sync.py)

Trigger case: GitHub #54 (bugs/15) is a bug report about document templates, so its body contains fenced blocks with literal `## Working directory` / `## Contents` / `## Acceptance Criteria` lines. After resolving with 'use GitHub', the next sync re-extracts the CFS doc's contents but resets at the embedded `## Contents` inside the fence, producing a different canonical body than GitHub's — so the conflict reappears forever. Resolving with 'use CFS' would instead overwrite the GitHub issue with a truncated body (data loss).

## Acceptance criteria

- Section extraction and issue-body splitting ignore heading-like lines inside fenced code blocks (``` and ~~~).
- A resolved conflict stays resolved: after applying either resolution, the next sync detects no conflict for the same content (round-trip convergence), including for the real bugs/15 / #54 content shape.
- Regression tests cover fenced headings in extract_document_sections, build_github_issue_body, and _split_github_issue_body, plus an end-to-end convergence test.

## Acceptance criteria

<!-- DONE -->
