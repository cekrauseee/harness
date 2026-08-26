# Pull Request Standard

## Title

Use:

```text
<type>(<optional-scope>)<optional-!>: <concise imperative English description>
```

Allowed types are `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `style`, `chore`, and `revert`. Use `chore` only when no specific type applies. Keep the title at 72 characters or fewer and omit a terminal period.

The title represents the principal outcome of the complete pull request, not necessarily the type of every included commit.

The head branch must use `<type>/<short-kebab-case-slug>`, and that type must match the title's primary type. Never use host, agent, user, or machine prefixes such as `codex/` or `claude/`. Physical worktree directory names remain host-specific and do not affect the Git branch.

## Body

- **Goal:** State the outcome and motivation in one short paragraph.
- **Desired behavior:** List observable results and preserved invariants. Do not describe internal steps here.
- **Change map:** Route each changed responsibility to a precise path or area. Group mechanical files only when the target remains useful.
- **Verification:** List commands or checks actually run and their outcome. If a relevant check was not run, say `Not run` and give the reason.
- **Review focus:** Route the reviewer to the highest-value questions, boundaries, and risks. Name a path or area for every item.
- **Risks:** State known limitations, compatibility concerns, follow-up work, or `None identified` when that claim is supportable.

The description is a compact routing contract for review, not proof that the implementation is correct. It must match the actual diff and verification evidence. Do not include generated enthusiasm, an implementation diary, raw command output, speculative benefits, duplicated facts, or unsupported claims.

The renderer accepts change-map and review-focus items as `target=description`. It limits the goal to 600 characters, each item to 400 characters, each section to 12 items, and the complete body to 8,000 characters.

## Publication

Drafting and validation are local preparation. Creating a draft PR is still external publication and requires explicit authorization. Merging always requires separate authorization.
