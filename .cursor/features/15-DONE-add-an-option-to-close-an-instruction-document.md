# Add An Option To Close An Instruction Document

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents
Rather than just being able to mark an instruction document as done, there should be a feature where you can mark it as closed. The functionality should be similar when a mark-in is done. This will signify that the document will not be worked on, and the feature or fix will not be implemented. The closed document will live inside the same folder with the same name except it will be preceded by CLOSED. So for instance, `4-CLOSED-add-tailwindcss`.

## Acceptance criteria
- The ability to close an instruction document. 
- A closed instruction document should have the word CLOSED in the title is described above. 
- The close command should look something like: `cfs i features close 1`. Its structure should mimic that of the "complete" command.

<!-- DONE -->
