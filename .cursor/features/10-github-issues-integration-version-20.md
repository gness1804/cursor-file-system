---
github_issue: 6
---
# Github Issues Integration Version 20

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

I would like to integrate the CFS project with GitHub issues. This would involve a way of bi-directional editing between these two types of data. For instance, closing a GitHub issue would automatically mark the CFS issue as done, and vice versa. Same for creating a GitHub issue or a CFS issue. 

I'm envisioning A setup where each CFS issue corresponds to a GitHub issue. There will probably need to be a command such as `cfs gh sync` To bring the GitHub issues and cfs instructions into sync because it's not an automatic thing. It is when you enter a GitHub issue, it's not going to automatically update the CFS issue and vice versa. At least for the first pass of this feature, we probably do need this sync command. The sync command would make sure that any new GitHub issues lead to creating corresponding CFS issues. And any closed GitHub issues would close the corresponding CFS issue. And vice versa, the other way around. 

This initiative will need a plan to complete, as it would take multiple steps. When starting with this issue, please create a document in the progress folder under the .cursor directory. This document should outline the steps needed to complete the GitHub issues integration.

## Acceptance Criteria

- Running the sync command above synchronizes GitHub issues and CFS issues. 
- Every CFS issue will correspond to a GitHub issue, and vice versa. 
- There should be bidirectional syncing and functionality. For instance, when I close the CFS issue on the command line and then run the sync command, it closes the corresponding GitHub issue, and vice versa. 
- For new GitHub issues, when you run the sync command, the application will ask the user which category the issue should fit into (e.g., features, bugs, etc.). 
- The GitHub issue should have essentially the same text as the CFS issue, the Markdown which contains the description and acceptance criteria related to the particular issue. 
- The AI agent will create a plan of steps to tackle, which need to be signed off on before any work is started. 
