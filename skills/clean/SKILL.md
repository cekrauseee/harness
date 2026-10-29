---
name: clean
description: Remove owned temporary delivery resources after integration while preserving pending work and history.
---

# Clean

Use environment resource bindings and the actual Git/PR state to identify resources created for the work. Integration is the trigger for cleanup; it does not imply the entire work record is finished.

Check each temporary worktree and branch for uncommitted changes, unmerged commits, active consumers, and ongoing executions. Preserve anything still needed. Resolve ambiguity before a destructive operation; existing authorization covers clearly owned, integrated temporary resources.

Remove obsolete worktrees and their local/remote branches when safe. Close obsolete auxiliary PRs where appropriate; retain the history of integrated PRs. Do not delete arbitrary resources because their names resemble a task identifier.

Update Harness resource bindings through tools after the corresponding operation succeeds. Preserve useful decisions and context for continuous work. Archive the work separately only when that is the right continuity decision.

Report remaining resources that still have a reason to exist. Cleanup should leave a predictable environment, not conceal incomplete delivery.
