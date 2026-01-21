---
github_issue: 3
---
# Expand this project to include AI models/services other than Cursor.

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

Right now, as is evident from the name, this project is focused on Cursor. But we might expand it to different AI services such as Claude Code or Gemini. 

This could involve keeping the same basic opinionated file structure but giving it a different name and placing it in a different part of a given repo rather than the Cursor folder. The `cfs exec` command could be used with multiple AI services, not just with Cursor. For instance, running this exec command could prompt the user to select from one of the series of services. If they select Claude Code for instance, then it would automatically open up a new Claude Code session with the CFS document as the input document. 

This would probably involve setting up Cursor integration as the MVP, and then expanding beyond it. This service would help to make this a viable system that I could distribute to users. 

## Acceptance criteria
