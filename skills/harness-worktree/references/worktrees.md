# Worktree Semantics

## Allowed Types

| Type | Primary intent |
| --- | --- |
| `feat` | Add user-visible capability |
| `fix` | Correct faulty behavior |
| `docs` | Change documentation only |
| `refactor` | Restructure without changing behavior |
| `perf` | Improve performance |
| `test` | Change tests only |
| `build` | Change dependencies, build, or toolchain |
| `ci` | Change continuous integration |
| `style` | Change formatting without behavior changes |
| `chore` | Perform maintenance not covered above |
| `revert` | Revert an earlier change |

Use `chore` only when no more specific type applies.

## Rules

- Use English lowercase kebab-case for the slug.
- Describe the intended outcome, not the agent or implementation session.
- Do not use `codex/`, `claude/`, usernames, issue authors, or machine names.
- Keep external issue IDs only when the project requires them.
- Configure the base branch per project; otherwise use `main`.
- Treat long-lived base branches such as `main` as exceptions to task-branch naming.
- Create a separate Git checkout for the task and keep task setup, edits, generated files, and verification inside it.
- Let the active host choose the directory name, storage root, and native bookkeeping.
- Keep creation, validation, adoption, reuse, and retirement under the Harness protocol.
- Prefer host-native create and remove operations when they preserve the Harness plan and update native bookkeeping.
- Fall back to ordinary Git at the host-selected path when a native operation is unavailable or incompatible.
- Never place a worktree under Harness global state merely to satisfy this skill.
- Never remove a dirty worktree or delete its branch without separate authorization.

Conventional Commits specifies commit messages, not branches. The `type/slug` branch convention is a Harness extension using the same vocabulary. Physical worktree storage is host-specific; creation and lifecycle semantics remain portable Harness concerns.
