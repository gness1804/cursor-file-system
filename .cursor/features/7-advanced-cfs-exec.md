---
github_issue: 4
---
# Advanced Cfs Exec - integrate with Cursor

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

Right now, the command cfs exec simply gives the user a copy of the relevant document for the ~~Cursor~~ AI agent to run. It would be nice if instead this command could directly tell the agent to start working on this document. For instance, if you tell the agent `cfs exec bugs 1`, then it would automatically start working on the first item in the bugs directory.

I have found out that you can call the command `claude`  with an argument. So for example, `claude 'help me fix the bug where the program keeps crashing'` Passes that argument to a new Claude Code session. I want to take advantage of this behavior to enable the command cfs exec to start a session of Claude code. Later on, I could add in other AI agents, but the proof of concept should really be with Claude. 

The command `cfs exec features 2` will Initiate a new Claude code session with the contents of features 2 as a string that's been passed to it.  

## Acceptance criteria

- User can run a cfs exec command which will trigger Claude code with the full content of the corresponding CFS issue doc. 
- Post MVP, we need to support other agents as well, such as Cursor or Gemini. 
