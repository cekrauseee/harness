---
name: harness-pr
description: Draft and validate evidence-based pull requests with Conventional Commit titles and compact reviewer context. Use when preparing, reviewing, explicitly publishing, or updating a pull request.
---

# Harness Pull Request

Derive a truthful pull request title and body from the actual diff. Drafting is read-only; opening, updating, or publishing a pull request requires explicit authorization.

## Draft a Pull Request

1. Read applicable repository instructions and identify the intended base and head branches.
2. Inspect the complete diff against that base, the included commits, changed paths, desired behavior, and relevant verification output. Do not rely on the conversation alone.
3. Choose the primary Conventional Commit type and optional stable scope. The title type must match the semantic type in the head branch. Read [references/pull-requests.md](references/pull-requests.md) for the title and body rules.
4. Render a standard body:

   ```bash
   python3 scripts/render_pr.py \
     --branch "docs/artifact-routing" \
     --title "docs(harness): define artifact routing" \
     --goal "Give final HTML artifacts one canonical destination." \
     --behavior "Final artifacts are routed from the documentation index." \
     --change "docs/standards.md=Define the canonical artifact route." \
     --verification "Ran python3 -m unittest discover -s tests." \
     --review "docs/standards.md=Confirm the route is unambiguous and complete." \
     --risk "Existing project artifacts are not migrated."
   ```

5. Map each changed behavior to the smallest useful path or area. Group mechanical files only when one target remains precise enough to route review.
6. Write review focuses as questions or risks to verify, not claims that the change is correct.
7. Treat a failed branch or body check as a publication blocker. Never preserve or introduce host, agent, user, or machine prefixes such as `codex/` or `claude/` in the head branch.
8. Compare every statement with the diff and verification evidence. State unrun checks explicitly with a reason.
9. Return the draft when publication is not explicitly authorized.
10. Open or update the pull request only when explicitly requested. Re-read the remote result and report its URL.

## Required Shape

The title follows the same format as a Conventional Commit so a squash merge can reuse it:

```text
<type>(<optional-scope>)<optional-!>: <imperative English description>
```

The body is a compact review context contract with exactly these sections:

```markdown
## Goal

## Desired behavior

## Change map

## Verification

## Review focus

## Risks
```

Use concise English and keep each section distinct. Goal states the outcome and motivation. Desired behavior lists observable results or preserved invariants. Change map uses `target=description` inputs to show where responsibilities changed. Verification lists checks actually run. Review focus uses `target=description` inputs to route the reviewer to important questions or risks. Risks records limitations, migrations, unrun checks, or supported `None identified` claims.

The renderer limits the goal to 600 characters, each list item to 400 characters, each list to 12 items, and the complete body to 8,000 characters. Prefer a precise directory or subsystem target over exhaustive file lists when they share one responsibility. Do not repeat the same fact across sections, include an implementation diary, paste raw output, or claim tests, safety, or compatibility without evidence.

The head branch must use `<type>/<short-kebab-case-slug>`, and its type must match the pull request title type. Long-lived base branches such as `main` remain exempt because they are not head task branches.

## Authorization Boundary

- A request to draft, validate, or review a pull request is not authorization to publish it.
- Publishing includes draft pull requests, updates to existing pull requests, labels, reviewers, comments, and ready-for-review state.
- A request to publish a pull request is not authorization to merge it.
- Do not push a branch unless the user authorized the push required for publication.
