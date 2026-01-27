---
github_issue: 22
---
# Improve The Github Issues Sync System for Content Conflicts

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

The GitHub issues sync system for content conflicts is hard to understand and buggy. The colors are confusing, and it doesn't always seem like the differences match up to the reality. For instance, it'll say that it's updating a local CFS doc from GitHub issues, but yet there's no local change shown in the Git panel. We need to improve the content conflict system to work better. Maybe a more interactive type of environment would be better. We need to figure out how to improve it. 

One example is just now when I was syncing this repo's cfs issues with corresponding GitHub issues. There was a content conflict prompt that appeared, even after I had just resolved the same issue in a prior content conflict prompt. I hadn't made any changes since, so we're getting some false positives here. The content conflict system definitely is subpar. 

## Acceptance criteria
- The Content Conflict Resolution System in the GitHub Issues Sync should be clear, logical, and intuitive to the user, and clearly present the differences as they are accurately reflected.

<!-- DONE -->
