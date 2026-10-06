---
name: workflows-implement
description: Build or change project behavior, fix a bug, or apply review corrections within the authorized scope.
---

# Implement

Start from the requested behavior or concrete correction set. Use current context and the relevant project conventions; investigate only gaps that affect the change. Make routine implementation decisions independently within the authorized scope.

A small solo correction with sufficient context needs no plan or work directory. When project constraints are unknown and could affect the change, resolve the existing environment with this skill's `scripts/harness.py resolve --project /path/to/project`, consult its short map and follow applicable references. Do not initialize storage merely for discovery. When assigned a module, begin with the supplied front/module and necessary dependencies. Do not load the whole team, all knowledge or a new project survey. On resumption, compare relevant workspace facts with saved context and continue without an automatic recap.

Use focused planning when the implementation needs it; finishing that suboperation returns to implementation under the existing authorization. Commands and suboperations already covered by this workflow do not require a separate skill chain.

For review corrections, use the existing findings and their version. Determine whether each remains applicable to the current code; resolve, contest or report it as pending. Do not repeat the complete review before implementing. Preserve unrelated work and avoid incidental redesign. Apply supplied patches only after checking that their intended effect fits the current code.

Own technical verification. Apply the user's testing and QA policy and the project's requirements. Decide separately whether to run existing checks, author tests or perform flow QA; none follows automatically from every edit. New tests need a concrete uncovered behavior or regression worth protecting, not a function count or coverage target. Reuse valid evidence and stop when sufficient checks establish the outcome. Reopen verification for changed behavior, a failure or a concrete unresolved concern. Missing credentials leave live checks limited, not permission to create credentials.

Code, comments and project documentation must make sense without the agents' execution plan. Describe real concepts and behavior, not temporary module numbers or orchestration details.

Preserve decisions, investigation and continuation when losing the conversation would cause meaningful loss, even if no work record exists yet. Otherwise keep small work ephemeral. When continuation context exists, update its relevant entry at a useful milestone with changed facts, evidence references, remaining work and next action. Read [file contracts](references/file-context.md) only when creating or changing that structure; `scripts/harness.py` supports initialization and atomic shared writes. Finishing a module does not close the whole work.

Deliver the implemented behavior, relevant verification and material limitations. Implementation does not imply commit, push, PR, merge, release or deployment; carry out only those additional actions already authorized.
