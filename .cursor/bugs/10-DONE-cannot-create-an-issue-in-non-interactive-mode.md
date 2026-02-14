 # Cannot Create An Issue In Non Interactive Mode

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

When you're in non-interactive mode, such as interacting with an AI agent, and the agent tries to create a new CFS issue, it errors out. The reason is because the create issue functionality in CFS requires opening an editor. But that doesn't work in non-interactive mode. There needs to be a flag passed to the create command, such as -y or --f, Which bypasses the editor selection. If this is passed, then the editor, then the noninteractive application could simply pass in the whole content of the issue, the CFS issue, in the command and it will create the issue. While you're at it, this needs to be done with the edit command as well. 

## Acceptance criteria

- `cfs i <category> create` and `cfs i <category> edit` We'll have flags that can be passed in by a non-interactive application to create or edit issues without going through the editor.

<!-- DONE -->
