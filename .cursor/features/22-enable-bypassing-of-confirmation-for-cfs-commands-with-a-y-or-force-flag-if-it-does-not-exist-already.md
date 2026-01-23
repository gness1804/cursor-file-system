---
github_issue: 21
---
# Enable Bypassing Of Confirmation For Cfs Commands With A Y Or Force Flag If It Does Not Exist Already

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

We need to see if commands such as `cfs i complete features 3` and `cfs i bugs edit 4` Have a way to bypass the interactive mode, such as -y or --force. If not, we should add them. I was having trouble getting an LLM to perform these tasks because of the interactive mode tripping up the completion of the tasks. 

## Acceptance criteria

- CFS commands that require confirmation will have a flag that enables the user to bypass the confirmation. 
