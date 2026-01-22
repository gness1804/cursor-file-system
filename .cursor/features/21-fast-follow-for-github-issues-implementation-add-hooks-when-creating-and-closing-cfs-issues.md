---
github_issue: 19
---
# Fast Follow For Github Issues Implementation Add Hooks When Creating And Closing Cfs Issues

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

Right now, the command `cfs sync` syncs the state of CFS issues and GitHub issues. I would like to add hooks where when you create a CFS issue, it automatically creates the corresponding GitHub issue. And when you close a CFS issue, either via done or close, it will close the corresponding GitHub issue.

However we also have to be mindful of the fact that some people don't have GitHub accounts hooked up to this app. We also don't want to bug people every single time they create or close an issue to sign into GitHub. There should be a simple logic to check once that they're signing into GitHub. If they decline then don't bother them again but if they are signing into GitHub then use the hooks that I just described. 


## Acceptance criteria


- Creating a CFS issue will trigger a hook which creates the corresponding GitHub issue. 
- Marking a CFS issue as done or closed will close the corresponding GitHub issue.