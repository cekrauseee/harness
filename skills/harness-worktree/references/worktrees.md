# Worktree Convention

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

Conventional Commits specifies commit messages, not branches or worktrees. This naming system is a Harness extension using the same vocabulary.
