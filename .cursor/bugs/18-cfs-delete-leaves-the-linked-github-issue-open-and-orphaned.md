---
github_issue: 68
---
# Cfs Delete Leaves The Linked Github Issue Open And Orphaned

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

## The problem

`cfs i <category> delete <id>` removes the local document but leaves its linked
GitHub issue **open**. Since the document is gone, nothing can close that issue
afterwards — CFS no longer has a record that the link ever existed. The result is
an orphaned open issue that has to be closed by hand with `gh issue close`.

`complete` and `close` do not behave this way. All three end a document's life,
but only two of them tell GitHub.

## Where it is

- `delete_in_category` (`src/cfs/cli_instructions.py:492`) calls
  `documents.delete_document(...)` and nothing else.
- `documents.delete_document` (`src/cfs/documents.py:394`) is a bare
  `doc_path.unlink()`. It never reads the frontmatter, so it never sees
  `github_issue:`.
- By contrast, `complete_in_category` (`:694`) calls
  `_try_auto_close_github_issue(new_path)` at `:779`, and
  `close_in_category` (`:946`) does the same at `:1031`.

So the helper already exists and is already wired into the two sibling commands.
`delete` is simply not calling it.

## How to reproduce

1. In a repo with GitHub sync configured, `cfs i bugs create -t "throwaway"`.
   Note the issue number it prints.
2. `cfs i bugs delete <id> --force`.
3. `gh issue view <number> --json state` — still `OPEN`, with no document behind
   it.

Observed 2026-08-05 on a private repo; nothing about it is visibility-specific.

## Why it matters

The orphan is silent. `delete` prints a clean success message, so there is no
indication anything was left behind, and the issue only resurfaces later as a
stale entry nobody can trace to a document. It is also the harder direction to
recover from: after `complete`, the doc still exists and can be re-synced, but
after `delete` the `github_issue:` number is gone with the file.

## Suggested fix

Read the frontmatter and close the issue **before** unlinking, so a failed close
can still abort with the document intact:

1. In `delete_in_category`, call `_try_auto_close_github_issue(doc_path)` before
   `documents.delete_document(...)`.
2. Close with a comment noting the document was deleted rather than completed —
   the two outcomes mean different things to someone reading the issue later.
3. If the close fails (no `gh`, no network, no `github_issue:` in frontmatter),
   warn and continue. Deleting a local file should not hard-fail on GitHub being
   unreachable, but it must not be silent either.

## Worth deciding

Should `delete` **close** the issue or **delete** it? Closing is the safer
default and matches `complete`. Deleting the issue destroys any discussion on it
and is not reversible, so if it is offered at all it should be behind an
explicit flag.

## Acceptance criteria
