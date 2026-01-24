---
github_issue: 24
---
# Major Refactor Decouple From Cursor To Make The Application Agent Agnostic

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

Right now, as the name suggests, this application is cursor-focused. It creates its documents and folders in the root .cursor folder in a given repo. As this application can be used for more than one AI agent, however, we should decouple it from cursor. So instead of creating it in the.cursor folder, we should instead store all of its documents and resources in a new .cfs folder.   

The rules directory thus either wouldn't exist or would be specifically related to Cursor only. The latter would probably have to copy these rules into the.cursor folder. The rest of the resources in the new .cfs folder would be agent-agnostic. We might also want to add the ability to create the standard AI rules documents, which include Agents.md, Claude.md, Gemini.md, etc. This could be an automated behavior that would set up one or more of these files based on the application's main technologies, programming languages, file structure, main purpose, etc.   

## Acceptance criteria

- A new AI agent-agnostic structure for this application in a new .cfs folder.
- The ability to automate the creation of AI rules documents such as Claude.md from CFS. 
- Probably a brand-new repo to store this application, given that we're no longer going to be calling it Cursor File System. We will need to port over the history of the old cursor file system repo to the new repo, similar to what I did in porting over the history of the build_llm_karpathy repo to the friendly advice columnist repo. 
