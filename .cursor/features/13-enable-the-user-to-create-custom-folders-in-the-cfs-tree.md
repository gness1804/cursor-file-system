---
github_issue: 7
---
# Enable The User To Create Custom Folders In The Cfs Tree

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

Right now, CFS only works with the designated folders that are present in this file structure, but I would like for the user to have the ability to create new custom folders under the .cursor directory. The command will be something like `cfs instr custom create.` Then the new folder could be used in other commands. For instance, `cfs instr work complete 1`. The custom folder's name would be used like the name of any of the built-in folders in the commands. The program would still fail if you enter a folder name that does not exist. But a custom folder name would be usable with any of the normal CFS commands.   

## Acceptance criteria
- User will be able to create custom CFS categories that are not already built in. 
- User will be able to choose whether they want to persist the new category either in a particular repo only or across their entire machine. If the latter, there will need to be some sort of state management file so that CFS in all the repos across the machine knows that this new category exists. 
- If we ever have user accounts, we might allow users to persist new categories across multiple computers. But I think that this particular issue can be considered complete if we just have new categories persist in a particular repo and on an entire machine. 
