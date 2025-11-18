# Add cfs next command to automatically work on the next issue in a folder.

This command should automatically go to the first unresolved issue in a particular folder. It should show the title of the issue in the command line and then ask the user if they want to work on it. If they say yes, then the program should show the full issue in the command line and then copy it to the clipboard to use with the Cursor agent.

For example, the command `cfs instructions next bugs` should start working on the next bug, that is, the first incomplete bug. (This would be equivalent to running `cfs exec bugs 2` if the first unresolved issue in the bugs folder were `2-script-hangs-on-run`.)

If there are no more instructions to run in a particular folder, then the program should show a message such as, "All of the issues have been completed in this particular folder. Please choose another folder to work on."

<!-- DONE -->
