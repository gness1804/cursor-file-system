---
github_issue: 4
---
# Advanced Cfs Exec

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

Right now, the command cfs exec simply gives the user a copy of the relevant document for the Cursor agent to run. It would be nice if instead this command could directly tell the Cursor agent to start working on this document. For instance, if you tell the agent `cfs exec bugs 1`, then it would automatically start working on the first item in the bugs directory. 
