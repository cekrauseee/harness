---
name: git
description: Prepare branches, worktrees, commits, and pull requests with the user's delivery conventions.
---

# Git

Follow the repository's delivery workflow and the user's authorization. Preserve unrelated changes. Use Harness resource bindings to retain the repository, branch, PR, and any owned temporary worktree needed for delivery and cleanup.

## Pull requests

Deliver every repository change through a pull request, including small fixes, documentation, and configuration. Work on a change branch rather than committing directly to the integration branch. Open a draft PR once the first coherent commit is available and keep it updated throughout continuous work; do not wait for the whole ongoing purpose to finish. Local Harness records and other unversioned user state are maintained through their own tools.

Group changes that deliver one coherent outcome in the same PR. Separate independent contexts even when they arrive in the same conversation; do not create a PR for each small step of one change. Reuse an open PR while its purpose remains coherent. After it merges, synchronize and clean that delivery, then start the next change from the updated target branch in a new PR. The work record can continue across those deliveries.

## Worktrees

Prefer the repository's existing primary worktree, using the branch for the current PR. The primary worktree is a checkout location, not an instruction to work on `main`. Switch branches there for sequential work when it is clean and available. Create an additional worktree only when the user requests one or concrete concurrent work would conflict in the primary checkout. An open PR or an inactive branch alone is not evidence of parallel execution.

Before creating a worktree, resolve the selected Harness environment, its source repository binding, and the effective Harness data root. Use the root reported by `doctor` under the current `--root` or `HARNESS_ROOT` configuration; do not infer a new environment from the checkout directory. Create linked worktrees only at `<root>/environments/<environment>/code/repositories/<repository-resource>/worktrees/<checkout>`, with a unique checkout identifier, following the [record layout](../../docs/records.md#temporary-worktrees). Keep the primary checkout at its existing location.

Use Git to create the linked worktree, then register its actual path with `resource add --kind worktree --owned` in the selected environment, associating it with the work when applicable. Record the repository, branch, and PR relationship in that work's context. Keep those bindings available to cleanup; removing a binding alone does not remove a Git worktree.

Keep durable context outside checkout directories. Harness record operations exclude the worktree area, and environment archival waits until that area is empty. Existing worktrees at other registered locations can remain there until normal Git cleanup; do not relocate active checkouts to follow a new convention.

## Commits and review

Verify the effective author and committer with Git before committing. Resolve the user's identity from established repository/account evidence; use repository-local configuration when a correction is needed. Do not invent an identity or rely on a provider's default attribution.

Use Conventional Commit semantics. Examples: branch `feat/auth/refresh-session`, commit or PR title `feat(auth): refresh expired sessions`. Scope describes the product area, not a task code or agent assignment.

Commits and PRs describe the final product change. Exclude generated-by notices, automatic coauthor trailers, internal plans, task identifiers, agent topology, and abandoned conversational history. Inspect staged changes and public text for those residues.

A PR description gives a reviewer enough context to assess the change:

- The problem or trigger and the implemented behavior.
- Relevant changes to interfaces, data, compatibility, or deployment.
- Validation performed and material limitations.

Scale the description to the change and respect the repository template. Use actual newlines or body files for multiline text. Mark the PR ready when the agreed change and required checks are complete. A ready PR does not itself authorize its merge. When a merge is confirmed, including one performed by the user, use `clean` to synchronize the local target and remove integrated temporary resources while retaining PR history.
