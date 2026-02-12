---
github_issue: 30
---
# CFS Sync is creating multiple issues.

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

The cfs sync feature seems to be creating multiple issues. It often happens when working with an AI agent so I'm not sure whether the problem's with the agent or with the CFS application. I'm thinking the problem is with CFS. Often when I try to close out an issue or run sync, I see multiple of the same issue, with the same number. We need to look into this potential bug and also make it harder to create CFS issues with the same numbers (duplicates). The ID should be unique for each issue in a CFS file. At the very least, there should be a duplicate check hook when you try to create or close an issue to ensure that there are no duplicates. Looking at both the ID and the content of a ticket title. Checks should also be able to be run manually. But this check really is just a band-aid. Ideally, the fix here would be more than a workaround, but it would solve whatever the root problem is. 

See screenshot for details. 


## Acceptance criteria


- CFS will no longer create or allow duplicate documents, duplicates being defined as documents having the same ID and/or the same title. 

<img width="752" height="638" alt="Image" src="https://github.com/user-attachments/assets/f67d4ebd-cf3e-4be0-8a9b-76fcf6c12213" />

<!-- DONE -->
