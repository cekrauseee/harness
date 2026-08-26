# Conventional Commit Standard

## Types

| Type | Use |
| --- | --- |
| `feat` | New user-visible capability |
| `fix` | Bug fix |
| `docs` | Documentation-only change |
| `refactor` | Internal change without new behavior or a bug fix |
| `perf` | Performance improvement |
| `test` | Test-only change |
| `build` | Dependency, build, packaging, or toolchain change |
| `ci` | Continuous integration change |
| `style` | Formatting-only change |
| `chore` | Maintenance not covered by another type |
| `revert` | Revert a prior change |

`feat` and `fix` carry the semantics defined by Conventional Commits 1.0.0. The remaining allowlist is a Harness policy. `chore` is the last resort.

## Examples

```text
feat(auth): add token refresh support
fix(api): reject expired sessions
docs(harness): explain artifact routing
refactor(storage): simplify cache invalidation
feat(api)!: replace the authentication contract

BREAKING CHANGE: clients must now provide a refresh token.
```

## Classification

Classify the result, not every file type:

- A feature with tests and documentation remains `feat`.
- A bug fix with a regression test remains `fix`.
- A documentation-only change is `docs`.
- A dependency update is normally `build`, not `chore`.
- A pure CI workflow change is `ci`.

Use a scope only when it is a stable project concept. Do not use a host, agent, contributor, ticket status, or temporary worktree as the scope.

## Cross-surface semantics

- Branches use the same allowed type vocabulary as commit headers.
- Task branches use `<primary-type>/<short-kebab-case-slug>` without host, agent, user, or machine prefixes.
- Each cohesive commit keeps the type that truthfully describes its own change. Supporting commits may differ from the task's primary type.
- The pull request title and task branch must share the task's primary type.
