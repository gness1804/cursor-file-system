---
github_issue: 59
---
# Promote Categories To Top Level Commands Cfs Category Verb Id

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

Building on the noun-first grammar from refactors/5 (#16), drop the required `instructions`/`instr`/`i` namespace so categories work directly at the top level: `cfs bugs complete 7`, `cfs features create`, `cfs bugs next`, etc.

Design decisions (agreed in discussion):

- **Keep `i`/`instr`/`instructions` as permanent aliases, not deprecated.** Muscle memory, CLAUDE.md files across repos, and CFS's own generated prompts (`cfs i <cat> complete <id> --force`) all use them. Both forms are canonical; docs prefer the short top-level form. Implementation is free: register the same Typer category apps on both the main app and the instructions app.
- **Extend RESERVED_CATEGORY_NAMES to cover the top-level namespace**: `init`, `version`, `tree`, `view`, `exec`, `gh`, `rules` (plus the verbs already reserved). Custom categories must not shadow top-level commands, and future top-level commands should be chosen from / added to this list to avoid breaking custom categories.
- **Promote `handoff` and `category` groups too**: `cfs handoff pickup`, `cfs category create <name>`, etc.
- **Unify `cfs view` semantics while we're in there**: top-level `cfs view` currently means 'incomplete only' (alias of `cfs i view -i`) while `cfs i view` shows everything. Decide on one behavior and make both forms match.

## Acceptance criteria

- `cfs <category> <verb> [id] [flags]` works for all built-in and custom categories, with identical behavior to `cfs i <category> <verb>`.
- `cfs i`/`cfs instr`/`cfs instructions` continue to work unchanged (no deprecation warnings).
- Custom categories cannot be created with names that collide with top-level commands.
- `cfs handoff ...` and `cfs category ...` work at the top level.
- `cfs view` and `cfs i view` have unified, documented semantics.
- Tests cover the new top-level forms, alias equivalence, and reserved-name rejection.
- README/AGENTS.md updated to present the top-level form as primary.

## Acceptance criteria

<!-- DONE -->
