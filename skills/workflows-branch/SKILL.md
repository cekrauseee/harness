---
name: workflows-branch
description: Prepare or create a Git branch whose name describes the intended change.
---

# Branch

Distinguish a naming/base proposal from a requested local branch operation. Establish the project, intended change and appropriate starting reference from current evidence. Inspect local changes and name collisions only as needed to preserve existing work. Do not reset, discard changes or silently reuse an unrelated branch.

Use `<type>/<main-title>` in English, with a concise lowercase hyphenated title: `feat/access-control`, `fix/session-expiry` or `docs/development-guide`. Honor an explicit alternative. The branch should remain semantically aligned with the intended PR; it need not repeat its title verbatim or change whenever the PR wording changes. Individual commits can have types different from the branch.

Create or select the branch within the authorized operation, preserving existing staged and unstaged work. Verify the resulting branch and base from the operation result or a targeted Git check. A branch can exist in the current checkout without another worktree. Opening a worktree may create its branch in the same operation; do not require duplicate user requests or separate rituals.

Return the branch name, relevant base and any collision or limitation. Branch work does not imply a work directory, agent creation, commit, push or PR.
