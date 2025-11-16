# And a cfs exec command that when run prompts a Cursor agent to execute the code in the document.

Example - you run the command `cfs exec bugs 1` and the agent executes the instructions in the relevant document with the ID of 1 in the bugs directory. In later versions, this would hopefully entail integration with the Cursor agent. But in an earlier version, this might simply entail the CLI program spitting out a custom instructions text that you can give to an agent to get started.

There should be a confirmation required to execute this command. Similar to the order subcommand, running `cfs-exec` should prompt the user to confirm that they really want to run this particular instruction document in the agent. It should show the title of the file. There should also be a `--force` option to bypass this behavior.

There should also be a `--next` option, which executes the next issue in the particular directory. For instance: cfs exec bugs next.

<!-- DONE -->
