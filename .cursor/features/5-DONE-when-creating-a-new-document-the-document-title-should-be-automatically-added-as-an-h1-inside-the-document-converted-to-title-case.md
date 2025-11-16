# When creating a new document, the document title should be automatically populated in title case.

When creating a new document, I want the document title to be automatically populated based on the name of the file. The title in the first line of the file should be converted to sentence case. Example: `cfs instructions bugs create` -> fix-annoying-lag -> Program should automatically add the following as the first line to the new file: `# Fix Annoying Lag`

The second line of the file should tell the Cursor agent which repository to work in.This should be the parent repository where the CFS commands are being called.

Then finally, the actual content of the file should be added if the user adds it on create. Otherwise, the user will add it separately to this document.

Example of the type of document that I want created:

```markdown
(for a new ticket created with the name of `fix-annoying-lag`)
# Fix Annoying Lag

## Working directory
`~/Desktop/examples/example-repo`

## Contents
Fix the annoying lag that's going on in the file `index.ts`. (...More details...)
```

Can you amend the file creation script to add this new information to each document created?

<!-- DONE -->
