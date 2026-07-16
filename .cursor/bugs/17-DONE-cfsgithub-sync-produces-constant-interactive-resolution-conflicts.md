---
github_issue: 65
---
# CFS/GitHub sync produces constant interactive-resolution conflicts

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

## Summary

Syncing CFS documents with GitHub issues produces conflicts that require interactive resolution far too often. In practice, a large share of ordinary CFS operations end with some variant of:

```
⚠ 1 item(s) need interactive resolution — run 'cfs gh sync' in a terminal.
```

This is disruptive enough that it has become a recurring tax on normal work rather than an occasional edge case.

## Why this is a problem

- **It interrupts otherwise clean workflows.** The prompt frequently appears as a side effect of a pre-commit hook, which means a routine `git commit` turns into "now go run `cfs gh sync` in a terminal and resolve something by hand."
- **It cannot be resolved in a non-interactive context.** Agents, CI, and any non-TTY shell can't complete the resolution, so the work stalls and gets deferred to a human, or the warning is simply ignored — which erodes trust in the sync state over time.
- **The conflicts are often not meaningful.** Being asked to arbitrate a "conflict" when a document was just created, or when the local and remote states are trivially reconcilable, feels like unnecessary ceremony rather than a real decision the user needs to make.
- **It trains users to ignore warnings.** A prompt that fires constantly stops carrying signal.

## Concrete recent example

In the `aws-security-specialty-exam` repo, a docs-only commit adding one new CFS progress document immediately produced a `Needs Interactive: 1` warning during the pre-commit hook — for a document that had just been created via `cfs i progress create`, and whose linked GitHub issue had been auto-created by CFS moments earlier. There was no genuine divergence for a human to arbitrate; CFS had authored both sides.

## What "better" would look like

Not prescribing an implementation, but the shape of a fix likely involves some combination of:

- **Auto-resolve the unambiguous cases.** If one side is strictly newer, or if CFS itself authored both sides in the same operation, reconcile without prompting. Reserve interactive resolution for genuine divergence (both sides independently edited since last sync).
- **Define a clear conflict model.** Be explicit about what counts as a conflict, what the source of truth is per field (title, body, state, labels), and which direction wins by default.
- **Offer a non-interactive resolution path.** Something like `cfs gh sync --strategy=local|remote|newer` or `--non-interactive`, so hooks, CI, and agents can complete a sync deterministically instead of deferring to a human.
- **Make the hook non-blocking / advisory.** A pre-commit hook probably should not be surfacing sync conflicts at all; at minimum it shouldn't imply the commit is in a bad state when it isn't.
- **Batch and defer.** Rather than prompting at commit time, accumulate pending reconciliations and let the user resolve them all at once, deliberately, when they choose to.


## Acceptance criteria


- Routine CFS operations (create, complete, close) on documents that CFS itself manages do not produce interactive-resolution prompts.
- A documented, deterministic, non-interactive sync path exists for hooks/CI/agents.
- Interactive resolution is reserved for true divergence, and when it does fire, the prompt explains *what* diverged and *why* it needs a human.

## Notes

Filed for later triage — not urgent, but it recurs constantly and is worth fixing properly rather than papering over.

<!-- DONE -->
