# Add command to automatically create a hand-off document for the next agent.

## Working repository

`~/Desktop/cursor-instructions-cli`

## Details

There should be a command like `cfs instructions handoff` that instructs the current agent to create a handoff document of what they have been working on that can then be picked up by a new agent. This can be useful in cases where the context window is almost full. The handoff document will be saved in the progress folder. You could even have a command like `cfs instructions handoff pickup` that you could tell the new agent that would let it know to start with the sirst incomplete handoff document in the relevant folder.

For version 1.0, this would probably entail printing out a list of instructions for the Cursor agent to create a handoff document. Version 2.0 would hopefully integrate directly with Cursor Agent for more seamless performance.

So the user would run `cfs instructions handoff`, which would then print out, on the command line, instructions for the Cursor agent to create a handoff document. These instructions would also be automatically copied to the user's clipboard. Then, the user could simply paste this command into the agent, which would let it know to create a detailed handoff document that a new agent could pick up. This new agent could then be instructed to pick up the handoff document by running `cfs instructions handoff pickup`.

