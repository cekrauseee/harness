# Engineering standards

## Language

Write repository-facing documentation, commit messages, branch names, and pull request content in English. Prefer simple words, active voice, short sentences, and factual claims.

## Conventional Commits

Use this form for commits and pull request titles:

```text
type(optional-scope)!: concise imperative description
```

Allowed types are `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `style`, `chore`, and `revert`. Use `chore` only when no specific type applies. Use `!` and a `BREAKING CHANGE:` footer for breaking changes.

## Branches and worktrees

Use `type/short-kebab-case-slug` for task branches. Do not include host names, agent names, or usernames.

Create task work in a separate checkout. Let the active host choose the directory, storage root, and native bookkeeping. Keep creation, validation, adoption, reuse, and retirement under the Harness protocol. Prefer host-native operations when they preserve the plan; otherwise use ordinary Git at the host-selected path. Keep task setup, edits, generated files, and verification inside that checkout.

Long-lived base branches such as `main` are exempt from task-branch naming.

## Pull requests

Use a Conventional Commit title and these body sections:

```markdown
## Summary

## Changes

## Verification

## Risks
```

Describe the actual diff. Never claim checks that did not run. Preparing a pull request does not authorize publication.

## Reviews

- `P0`: certain catastrophic data loss, critical security impact, or an operation blocker.
- `P1`: major correctness, security, or regression risk requiring urgent resolution.
- `P2`: relevant correctness, reliability, or maintainability defect.
- `P3`: localized low-risk defect worth fixing.

Report only evidence-backed, actionable findings with a tight file and line range, impact, and suggested direction. Review is read-only unless fixes are separately requested.
