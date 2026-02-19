---
github_issue: 41
---
# Cfs Sync Is Still Creating Duplicates

## Working directory

`~/Desktop/cursor-instructions-cli`

## Contents

In spite of the recent changes made to address the problem of duplicate creation, there are still duplicate CFS issues being created. For example:

```shell
FEATURES
                                                                                                                                       
  ID   Title                                                                                          Size   Modified           Notes  
 ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────── 
  1    DONE-out-to-file                                                                             6.1 KB   2026-01-16 14:29          
  2    DONE-add-ability-to-output-inference-result-in-the-outputs-directory                          480 B   2026-01-16 14:29          
  3    CLOSED-make-training-script-output-files-in-a-default-training-directory-inside-of-outputs    701 B   2026-01-17 11:00          
  4    DONE-write-script-to-run-inference-prompts                                                   3.6 KB   2026-01-16 14:29          
  5    DONE-re-organize-tier-s-examples-master-document-to-oversample-qa-pairs                      2.3 KB   2026-01-16 14:29          
  6    DONE-create-a-new-script-to-run-multiple-prompts                                             1.8 KB   2026-01-16 14:29          
  7    DONE-create-script-to-convert-new-documents-structure-into-json-l                            2.5 KB   2026-01-16 14:29          
  8    DONE-build-out-the-front-end-application-for-the-ai-advice-column-app                        3.7 KB   2026-01-17 11:00          
  9    add-the-ability-to-ask-the-model-follow-up-questions                                          619 B   2026-01-21 19:06          
  10   DONE-add-check-to-ensure-that-question-relates-to-interpersonal-and-relationship-issues      1.3 KB   2026-01-17 10:24          
  11   CLOSED-add-multiple-models-to-use-with-front-end-app                                           18 B   2026-02-16 20:22          
  12   DONE-add-ability-to-save-sessions-and-record-a-history-of-questions-that-you-asked           1.3 KB   2026-01-21 19:06          
  13   DONE-deploy-application-to-aws                                                                550 B   2026-02-16 20:22          
  15   DONE-post-deployment-fast-follow-custom-domain-cors-waf-and-cleanup                          1.2 KB   2026-02-16 20:22          
  15   post-deployment-fast-follow-custom-domain-cors-waf-and-cleanup                               1.2 KB   2026-02-16 20:22   
```

Note the two CFS issues with number 15. I'm thinking this is probably being caused by syncing with GitHub issues. We need to take a closer look at this to solve the problem.  

## Acceptance criteria

- CFS will not create duplicate issues. 
