---
name: workflows-commit
description: Draft commit messages or create requested cohesive Conventional Commits; implementation alone does not authorize committing.
---

# Commit

Match the requested result: message wording, staging plan or commit creation. A wording-only request remains read-only. Reuse the current diff and conventions; inspect status and affected changes when needed to establish scope and ownership.

Group files or hunks by cohesive intent. Preserve unrelated modifications and existing staging; never include another writer's work merely because it is staged. If the index mixes scopes, construct the intended commit without discarding that staging, or resolve a genuinely inseparable boundary with the user. Include relevant documentation and verification changes with the behavior they support.

Use English Conventional Commits: `type(scope): description`, with scope optional. For example, `feat(auth): enforce resource-level permissions`. A breaking change uses `!` before the colon or a `BREAKING CHANGE:` footer. The body is ordinary explanatory prose when useful, separated by a blank line. Classify each commit's actual change independently of the branch or PR type.

A commit request includes necessary staging, not amending, bypassing hooks, pushing or publication unless those are also authorized. Inspect the final staged scope and use sufficient verification, reusing valid results. Finish this operation when the requested commits are complete and continue any already-authorized outer task; do not add another audit merely because committing is the next step.

Return the resulting commit hashes and included scope, or the proposed message, with relevant remaining work.
