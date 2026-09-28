---
name: workflows-worktree
description: Create, reuse or retire a Git worktree inside the project environment.
---

# Worktree

For a requested plan, remain read-only. For creation, establish the project, base, intended branch and required destination before invoking a tool. Resolve a missing environment location with this skill's `scripts/harness.py resolve --project /path/to/project`; initialize it when needed for the authorized checkout.

All new worktrees must be inside `<environment>/worktrees/<readable-name>`. Check the supported host tool's destination behavior before creation. Use it when it can honor that location; otherwise use native Git when allowed by the host, or report the tool constraint. Never silently accept an external managed destination or claim that an unsupported path option exists. Keep checkouts outside knowledge searches.

Reuse the same front's checkout for continuation. For new work, prefer a suitable, known free checkout only after accounting for its changes and commits, confirming that no active front or process relies on it, and preparing the correct base/branch. Otherwise create a new worktree. Do not scan all environments or discard changes just to reuse one. Use a semantic branch such as `feat/access-control`; check collisions with native Git before creation.

Associate the path with the writing front's context when a front exists. A cooperating pair can alternate writes within that front; independent writing fronts use separate checkouts. Read [file contracts](references/file-context.md) only when creating that context. No file claims or per-action ownership updates are needed.

Confirm the resulting registered path, branch and starting revision. For authorized retirement, account for local changes, needed untracked/ignored files and commits before removal; use host archival where applicable and supported. Never force away meaningful work. Closing temporary cognitive material is a separate operation and does not authorize removing a checkout or branch.

Return the path and branch, or the concrete obstacle.
