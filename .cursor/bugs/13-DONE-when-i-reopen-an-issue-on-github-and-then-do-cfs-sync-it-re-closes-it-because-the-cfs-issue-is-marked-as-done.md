---
github_issue: 50
---
# When I Reopen An Issue On Github And Then Do Cfs Sync It Re Closes It Because The Cfs Issue Is Marked As Done

## Working directory

`~/conductor/workspaces/cursor-instructions-cli/khartoum`

## Contents

When there's a closed issue on GitHub that I discover I want to work on again (for example, a bug that reappears), then I re-open that issue in GitHub in the browser. The problem is that when I then run `cfs gh sync`, it re-closes the GitHub issue because the local CFS issue is done. I want to change this behavior so that if an issue on GitHub has been reopened, it will reopen the issue locally in CFS. 

## Acceptance criteria

- When I reopen an issue on GitHub and then run `cfs gh sync`, it will reopen the local CFS issue.

<!-- DONE -->
