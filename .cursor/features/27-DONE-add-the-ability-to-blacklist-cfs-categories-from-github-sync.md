---
github_issue: 34
---
# Add The Ability To Blacklist Cfs Categories From Github Sync

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

We need to enable a user to be able to blacklist certain CFS categories from GitHub Sync. For instance, if some of their CFS documents are sensitive and they don't want them going into source control. An example might be the new security folder. Putting something in a security folder as a vulnerability is basically advertising to people on GitHub that this application has these vulnerabilities. I think the security folder at a minimum should be blacklisted by default. This means that it would not be included in GitHub sync unless the user explicitly overrode this behavior. 

## Acceptance criteria

- Exclude the security folder from GitHub sync by default. 
- Allow the user the option to override this behavior. 
- Allow the user to optionally specify which other folders to exclude from GitHub sync.

<!-- DONE -->
