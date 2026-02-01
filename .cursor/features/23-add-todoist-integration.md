---
github_issue: 26
---
# Add Todoist Integration

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

We already have two-way syncing between CFS issues and GitHub issues. It will be nice to add Todoist integration as well. Issues from , CFS, could bidirectionally sync with Todoist. The tricky part would be to also integrate GitHub issues in a 3-way sync. But for the first pass, we might just integrate Todoist issues in a two-way sync with CFS issues, or simply have CFS issues create Todoist issues and then not have those sync at all with CFS issues or GitHub issues. 

## Acceptance criteria

- CFS issues will produce corresponding Todist tasks. 
- Beyond the first pass, we might have syncing between GitHub issues, CFS issues, and Todoist tasks. 
- Use the Todoist API or an MCP, whichever is the best tool for the job. 
