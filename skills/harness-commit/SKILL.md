---
name: harness-commit
description: Classify changes, prepare and validate English Conventional Commit messages, and create commits only with explicit authorization. Use when a user asks to name, organize, validate, or create one or more Git commits.
---

# Harness Commit

Prepare cohesive commits with English Conventional Commit messages. Message preparation is read-only; creating a commit requires explicit authorization and never implies pushing it.

## Prepare a Commit

1. Read applicable repository instructions.
2. Inspect `git status`, the relevant staged and unstaged diffs, and recent commit style. Do not stage unrelated user changes.
3. Group changes by one primary intent. Prefer multiple cohesive commits over one message that hides unrelated changes.
4. Choose the type and optional stable scope. Read [references/conventional-commits.md](references/conventional-commits.md) when classification is ambiguous.
5. Write a concise English imperative description, then validate it:

   ```bash
   python3 scripts/validate_conventional.py \
     --message "docs(harness): define artifact routing" \
     --branch "docs/artifact-routing"
   ```

6. Report the proposed grouping and message when commit authorization is absent.
7. Run `git commit` only when the user explicitly requested a commit. Recheck the staged diff immediately before committing and report the resulting hash.

## Format

```text
<type>(<optional-scope>)<optional-!>: <imperative English description>

<optional body>

<optional footer(s)>
```

- Use lowercase type and scope.
- Keep the header at 72 characters or fewer and omit a terminal period.
- Use `!` and/or a `BREAKING CHANGE:` footer for a breaking change.
- Use `docs` only for documentation-only changes and `chore` only as a fallback.
- Treat tests or documentation accompanying a feature or fix as part of that feature or fix.

The validator enforces structure, allowed types, ASCII text, and branch syntax. The agent must still verify that the description is truthful, English, imperative, and aligned with the actual diff.

## Authorization Boundary

- Do not stage, commit, amend, rebase, reset, push, tag, or publish without authorization for that action.
- A request to draft or validate a message is not authorization to commit.
- A request to commit is not authorization to push.
- Never bypass hooks unless the user explicitly requests it and understands the consequence.
