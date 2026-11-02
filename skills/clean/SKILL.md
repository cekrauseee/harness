---
name: clean
description: Remove owned temporary delivery resources after integration while preserving pending work and history.
---

# Clean

Treat cleanup as part of each merged delivery. Act when a merge is confirmed, including one performed by the user, without requiring a separate cleanup request. Use environment resource bindings and the actual Git/PR state to identify the repository, target branch, merged source branch, and owned temporary worktrees. A closed but unmerged PR is not evidence of integration. A merge does not imply the entire work record is finished.

Fetch the repository and synchronize the local merge target with its remote using a fast-forward when possible. Use the primary worktree when it is available; do not interrupt another active checkout or overwrite local changes to switch branches. Inspect divergence instead of resetting the local target. If synchronization must wait, report the reason and preserve the pending action in the work record.

Before deletion, check each temporary worktree and branch for uncommitted changes, commits added after the merged PR, active consumers, and ongoing executions. Confirm that the candidate branch's work was integrated. Account for squash and rebase merges: ancestry alone can be insufficient, so use the merged PR's recorded head and content when verifying integration. Preserve anything still needed. Resolve ambiguity before deletion; existing authorization covers clearly owned, integrated temporary resources.

Leave the merged feature branch before deleting it and run removal from a retained checkout. Remove owned temporary worktrees through Git, then remove the integrated local and remote feature branches after confirming they have no newer work. Keep the primary worktree and integration branches. Close obsolete auxiliary PRs where appropriate; retain the history of integrated PRs. Do not delete arbitrary resources because their names resemble a task identifier.

Update Harness resource bindings through tools after the corresponding operation succeeds. Remove owned temporary artifacts and empty worktree directories that are no longer needed. Preserve useful decisions and context for continuous work; its next delivery uses a new branch and PR. Archive the work separately only when that is the right continuity decision.

Report synchronization, removed resources, and anything retained with its concrete reason. Cleanup should leave a predictable environment, not conceal incomplete delivery.
