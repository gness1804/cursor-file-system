---
github_issue: 20
---
# CFS issues that are not properly formatted don't transfer any text to their corresponding GitHub issue.

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

The CFS issue has to be properly formatted with text and the ## Contents or ## Acceptance criteria sections for the text to go to the GitHub issue. If the text is elsewhere the GitHub issue is still created but there's no body text in it. We need to fix this so that body text from improperly formatted CFS issues is also transferred. Probably such text should just go into the main body of the GitHub issue.

## Acceptance criteria

- CFS issue text will be properly transferred to the corresponding GitHub issue, even if the CFS document is not properly formatted with the expected headers.

<!-- DONE -->
