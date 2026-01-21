---
github_issue: 10
---
# Add Claude Code Integration

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

Right now, this project is set up for Cursor. But it can be modified to also work with Claude code. In particular, the `cfs exec` Command might be integrated with Claude Code. So for example, running `cfs exec bugs 2` Would automatically load the relevant instruction file and tell Claude Code to start working on it. This could be a powerful feature that users could use in building out projects.  

## Acceptance criteria

- A modification to the current project which integrates into Claude Code. 
- The integration should enable running the cfs exec command against a particular instruction document, which would automatically send the document to Claude Code and instruct Claude Code to start working on. 
- There should be a confirmation step after the user enters the cfs exec command that asks the user to confirm that they really want to execute this particular command. Typical confirmation logic should apply here. 
- Post-MVP might include other integrations such as with Claude.md. But the MVP is the Exec feature mentioned above. 
