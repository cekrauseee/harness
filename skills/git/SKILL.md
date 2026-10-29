---
name: git
description: Prepare branches, worktrees, commits, and pull requests with the user's delivery conventions.
---

# Git

Follow the repository's delivery workflow and the user's authorization. Preserve unrelated changes. Use worktrees when isolation helps the requested work; record owned temporary resources in the environment so cleanup can identify them later.

Verify the effective author and committer with Git before committing. Resolve the user's identity from established repository/account evidence; use repository-local configuration when a correction is needed. Do not invent an identity or rely on a provider's default attribution.

Use Conventional Commit semantics. Examples: branch `feat/auth/refresh-session`, commit or PR title `feat(auth): refresh expired sessions`. Scope describes the product area, not a task code or agent assignment.

Commits and PRs describe the final product change. Exclude generated-by notices, automatic coauthor trailers, internal plans, task identifiers, agent topology, and abandoned conversational history. Inspect staged changes and public text for those residues.

A PR description gives a reviewer enough context to assess the change:

- The problem or trigger and the implemented behavior.
- Relevant changes to interfaces, data, compatibility, or deployment.
- Validation performed and material limitations.

Scale the description to the change and respect the repository template. Use actual newlines or body files for multiline text. Once integrated, use `clean` for owned temporary resources while retaining PR history.
