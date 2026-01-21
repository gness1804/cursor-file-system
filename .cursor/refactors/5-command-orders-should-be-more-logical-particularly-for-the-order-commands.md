---
github_issue: 16
---
# Command Orders Should Be More Logical Particularly For The Order Commands

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

The command order needs to be more logical. For example, in order to change the order of a particular folder, you have to run `cfs instr order features.`. This violates the usual rule that the first argument after `cfs instr` Should be a folder/category name rather than an action. More generally, we need to do an audit of our existing commands and see if they can be laid out in a more logical way. Even as the creator of the program, I often struggle to remember the order of the commands. Given this, it's hard to think that new users would have an easy time of it. 

This ticket will be an iterative effort between the user and the Cursor AI. The Cursor AI should first audit all the existing commands and then suggest ones that could be made more logical. The overall goal is to keep a uniform order to the commands as much as possible. If necessary, we should research best practices for a modern CLI in this respect.
