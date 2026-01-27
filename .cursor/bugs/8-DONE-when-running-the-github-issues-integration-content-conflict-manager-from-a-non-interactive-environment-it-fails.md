# When Running The Github Issues Integration Content Conflict Manager From A Non Interactive Environment It Fails

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

Normally when you run `cfs gh sync`, It presents you with a diff viewer and an option to resolve the conflicts if the CFS version of an issue conflicts with the GitHub issues version. The problem is that I'm starting to use this command as part of a Git hook. This is a non-interactive environment. We need to decide on the best behavior to handle this. One option might be to skip the conflict resolution whenever there is a conflict when this command is run in a non-interactive environment, but it will give you a warning after the commit saying that you have to go back and fix the conflict. Another option is simply to throw an error and fail the commit. 

## Acceptance criteria
- When the command `cfs gh sync` Is run in a non-interactive environment, it will either fail gracefully or it will show a clear warning that the user has to run this in the future. 
