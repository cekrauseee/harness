---
name: harness-pr
description: Draft and validate evidence-based pull requests with Conventional Commit titles. Use when preparing, reviewing, explicitly publishing, or updating a pull request.
---

# Harness Pull Request

Derive a truthful pull request title and body from the actual diff. Drafting is read-only; opening, updating, or publishing a pull request requires explicit authorization.

## Draft a Pull Request

1. Read applicable repository instructions and identify the intended base branch.
2. Inspect the complete diff against that base, the included commits, and relevant verification output. Do not rely on the conversation alone.
3. Choose the primary Conventional Commit type and optional stable scope. Read [references/pull-requests.md](references/pull-requests.md) for the title and body rules.
4. Render a standard body:

   ```bash
   python3 scripts/render_pr.py \
     --title "docs(harness): define artifact routing" \
     --summary "Define where final user-facing HTML artifacts belong." \
     --change "Route final HTML files to docs/artifacts/." \
     --verification "Ran python3 -m unittest discover -s tests." \
     --risk "Existing project artifacts are not migrated."
   ```

5. Compare every statement with the diff and verification evidence. State unrun checks explicitly with a reason.
6. Return the draft when publication is not explicitly authorized.
7. Open or update the pull request only when explicitly requested. Re-read the remote result and report its URL.

## Required Shape

The title follows the same format as a Conventional Commit so a squash merge can reuse it:

```text
<type>(<optional-scope>)<optional-!>: <imperative English description>
```

The body contains exactly these sections:

```markdown
## Summary

## Changes

## Verification

## Risks
```

Use concise English and describe the resulting change rather than the work session. Never claim tests, review, compatibility, migration, or safety that was not verified.

## Authorization Boundary

- A request to draft, validate, or review a pull request is not authorization to publish it.
- Publishing includes draft pull requests, updates to existing pull requests, labels, reviewers, comments, and ready-for-review state.
- A request to publish a pull request is not authorization to merge it.
- Do not push a branch unless the user authorized the push required for publication.
