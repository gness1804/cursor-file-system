---
github_issue: 54
---
# `-c/--content` inconsistent between create/edit; `edit -c` destroys frontmatter + title

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

## Summary

The `-c/--content` flag is handled **inconsistently** between `create` and `edit`, and `edit -c` is **destructive**: it overwrites the entire document with the raw content string, discarding the YAML frontmatter (including `github_issue:`) and the title. Separately, `create -c` silently wraps the content in a fixed template, so passing already-structured content produces duplicated section headers.

Hit while creating CFS docs non-interactively (via an AI agent) in `cfs version 0.10.0`.

## Environment

- `cfs version 0.10.0`
- macOS

## Repro A — `create -c` wraps content in a template (causes duplicate sections)

```
cfs i <category> create -t "Repro" -c "MY BODY LINE ONE"
```

Resulting file:

```markdown
# Repro

## Working directory

`~/Desktop/receipt-ranger`

## Contents

MY BODY LINE ONE


## Acceptance criteria

```

So `-c` content is inserted into the **Contents** section of a fixed scaffold. A user writing a *complete* document (with their own `## Working directory` / `## Acceptance criteria`) ends up with **duplicated headers** — e.g. two `## Working directory` blocks and two `## Acceptance criteria` blocks (one filled, one empty).

## Repro B — `edit -c` replaces the WHOLE file verbatim (drops title + frontmatter)

Starting from a normal doc that has frontmatter + title + sections:

```
cfs i <category> edit 1 -c "NEW BODY ONLY"
```

Resulting file (entire contents):

```
NEW BODY ONLY
```

The title (`# ...`), all template sections, **and the YAML frontmatter** (`---\ngithub_issue: ...\n---`) are gone.

## Impact

- **Data loss / sync breakage (most serious):** because `edit -c` strips frontmatter, the `github_issue:` linkage is silently destroyed. For a non-hidden category, a subsequent `cfs gh sync` would no longer associate the doc with its existing GitHub issue (risking a duplicate issue, or a broken `complete` → close-issue flow).
- **Inconsistency:** `create -c` treats the string as *body within a template*, while `edit -c` treats it as *the entire file*. A user can't use the same content string for both, and round-tripping (create then edit) changes the document's structure.
- **Boilerplate duplication:** `create -c` with structured content yields duplicate `## Working directory` / `## Acceptance criteria` headers, requiring a manual cleanup pass.

## Suggested fix

1. Make `edit -c` **preserve the existing frontmatter and title**, replacing only the body (or, at minimum, never silently drop frontmatter — re-emit the `---` block).
2. Make `create -c` and `edit -c` consistent about what the content string represents (both "body of the document" or both "full file"), and document it in `--help`.
3. If `create -c` keeps templating, either skip injecting sections the content already provides, or document that `-c` should contain only the Contents-section body.

Happy to provide more detail or a PR if useful.
