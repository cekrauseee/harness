---
name: workflows-implement
description: Implement an authorized change or address a defined set of review findings and corrections.
---

# Implement

Start from the requested behavior or concrete correction set. Use current context and the relevant project conventions; investigate only gaps that affect the change. Make routine implementation decisions independently within the authorized scope.

A small solo correction needs no plan, environment lookup or work directory unless useful context or coordination must persist. When assigned a module, read the supplied front context, that module and necessary dependencies. Do not load the whole team, all knowledge or a new project survey. On resumption, compare the relevant workspace facts with saved context and continue without an automatic recap.

For review corrections, use the existing findings and their version. Determine whether each remains applicable to the current code; resolve, contest or report it as pending. Do not repeat the complete review before implementing. Preserve unrelated work and avoid incidental redesign. Apply supplied patches only after checking that their intended effect fits the current code.

Own technical verification. Follow the project's applicable checks, reuse valid evidence and stop when sufficient checks pass. Reopen verification only for changed behavior, a failure or a concrete unresolved concern. Browser or manual visual QA remains opt-in; do not start a dev server solely for it without authorization. Missing credentials leave live checks limited, not permission to create credentials.

Code, comments and project documentation must make sense without the agents' execution plan. Describe real concepts and behavior, not temporary module numbers or orchestration details.

When continuation context exists, update only the relevant front at a useful milestone: changed facts, evidence references, remaining work and next action. Read [file contracts](references/file-context.md) only if its structure must be created or changed; `scripts/harness.py` is available for atomic shared writes. Finishing a module does not close the whole work.

Deliver the implemented behavior, relevant verification and material limitations. Implementation does not imply commit, push, PR, merge, release or deployment; carry out only those additional actions already authorized.
