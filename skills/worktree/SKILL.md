---
name: worktree
description: "Create, reuse or retire a Git worktree and its branch for isolated or parallel work, recording it in the Harness front context. Use when asked for a worktree, an isolated checkout, or a separate branch for a front."
---

# Worktree

Establish the project, the base, the intended branch and the destination before running anything; for a requested plan only, stay read-only.

Branch names follow the owner's convention, by default `<type>/<slug>` such as `feat/access-control`; check collisions with native Git first. Opening a worktree creates its branch in the same operation, so the branch needs no separate request or skill.

Worktrees created here go under the environment's `worktrees/<readable-name>` by default; `python3 scripts/harness.py resolve --project /path/to/project` (this skill's helper, by absolute path) returns that path, and `init` establishes the environment when the checkout needs it. Worktrees the host manages are accepted where they are, since any checkout listed by `git worktree list` resolves to the same environment. Record the path, branch and starting revision in the writing front's `context.md` when a front exists; a cooperating pair can alternate writes in one front, and independent writing fronts use separate checkouts. Read [file contracts](references/file-context.md) only when creating that context.

Reuse the same front's checkout for continuation. Reuse a known free checkout for new work only after accounting for its changes and commits, confirming that no front or process relies on it, and preparing the right base and branch; otherwise create a new one. Preserve existing staged and unstaged work; a clean checkout is never worth a reset or discarded changes.

Hosts:
- Claude Code: `EnterWorktree` creates under `.claude/worktrees/` and asks before adopting a path elsewhere; use `git worktree add` for an environment destination and let the session adopt it when needed. Worktrees the desktop app creates for a session stay as they are.
- Codex: the app creates managed worktrees under its configured root and the agent cannot choose that location; use `git worktree add` for a front checkout at the environment path when isolation beyond the session is needed.

For retirement, account for local changes, needed untracked or ignored files and unmerged commits before removal, use the host's archival where it exists, and never force away meaningful work. Closing work context is a separate operation that removes no checkout or branch.

Return the path, branch and starting revision, or the concrete obstacle, then continue the task that needed the checkout.
