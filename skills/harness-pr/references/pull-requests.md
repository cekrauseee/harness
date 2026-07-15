# Pull Request Standard

## Title

Use:

```text
<type>(<optional-scope>)<optional-!>: <concise imperative English description>
```

Allowed types are `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `style`, `chore`, and `revert`. Use `chore` only when no specific type applies. Keep the title at 72 characters or fewer and omit a terminal period.

The title represents the principal outcome of the complete pull request, not necessarily the type of every included commit.

## Body

- **Summary:** Explain the outcome and motivation in one short paragraph.
- **Changes:** List concrete changes visible in the diff.
- **Verification:** List commands or checks actually run and their outcome. If a relevant check was not run, say `Not run` and give the reason.
- **Risks:** State known limitations, compatibility concerns, follow-up work, or `None identified` when that claim is supportable.

Do not include generated enthusiasm, implementation diary, raw command output, speculative benefits, or unsupported claims.

## Publication

Drafting and validation are local preparation. Creating a draft PR is still external publication and requires explicit authorization. Merging always requires separate authorization.
