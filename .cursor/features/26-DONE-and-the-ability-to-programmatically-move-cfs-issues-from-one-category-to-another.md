---
github_issue: 33
---
# And The Ability To Programmatically Move Cfs Issues From One Category To Another

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

Right now, the only way to change the CFS category from one issue to another is to manually move the file and then rename it based on the number sequence in the new file. This is cumbersome and error-prone. We need a more programmatic solution for this. This would involve entering in the name of the existing issue plus the name of the new category you want to move it to. The app should take care of the rest.

## Acceptance criteria

- When the user enters in a command such as `cfs i move features 1 security`, The application will move the CFS issue from the features directory with ID of 1 to the security directory. 
- During the process of moving the document from one directory to another, the application will take care of all the numbering ID logic. For instance, if you move the item with ID 10 from the features folder into an empty security folder, then the application will rename the other files in the features folder to reflect the fact that number 10 is gone. So #11 becomes #10, #12 becomes #11, etc. And likewise, the same logic should be applied in the destination folder.

<!-- DONE -->
