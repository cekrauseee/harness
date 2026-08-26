---
name: harness-review
description: Review code, documentation, commits, or pull requests read-only with compact context routing. Use for diff review, risk assessment, or change validation that requires evidence-backed P0-P3 findings.
---

# Harness Review

Review for concrete defects and risks. Reviews are read-only by default: identify actionable findings without changing files, commits, branches, pull requests, or external state.

## Review Procedure

1. Establish the requested scope and applicable repository rules.
2. For a pull request, read its Goal, Desired behavior, Change map, Verification, Review focus, and Risks before opening surrounding repository context. Treat this description as routing context, not evidence.
3. Inspect the complete diff and compare every changed path with the Change map. Never skip a changed file because the description omitted it.
4. Start with the listed review targets, changed paths, and their immediate dependency boundaries. Do not scan the repository by default.
5. Expand only when the diff crosses a public API, authorization, data, concurrency, configuration, migration, or compatibility boundary; a direct caller or callee is needed; tests contradict the contract; or the map is stale or incomplete.
6. Verify each suspected issue. Trace inputs, control flow, affected callers, and existing tests instead of relying on the description or pattern matching alone.
7. Classify actionable findings with [references/review-severity.md](references/review-severity.md).
8. Keep line ranges tight and ensure the cited line is part of, or directly explains, the defect.
9. Optionally validate structured findings before rendering them:

   ```bash
   python3 scripts/validate_review.py findings.json
   ```

10. Present findings in priority order. If none remain after verification, state that no actionable findings were found and mention any material contract or verification gap.

## Context Discipline

- The complete diff is mandatory; a repository-wide scan is not.
- Use the PR contract to order inspection and bound surrounding context, never to reduce source verification.
- Treat missing or inaccurate contract content as a review gap. Report it separately unless it creates a concrete product or engineering defect.
- Stop loading context once desired behavior, changed responsibilities, dependency boundaries, and verification coverage are understood well enough to confirm or reject findings.

## Finding Contract

Each finding contains:

```text
[P2] Handle the empty-token path
path/to/file.py:42

Evidence: ...
Impact: ...
Direction: ...
```

- Use an imperative, concise title without a terminal period.
- Explain observable evidence or a reproducible path.
- State the concrete impact, not a vague quality concern.
- Suggest direction without prescribing a large unrelated rewrite.
- Do not report praise, summaries, stylistic preference, speculative edge cases, or issues already prevented elsewhere.

## Mutation Boundary

- A review request does not authorize fixes, formatting, commits, comments, approvals, or requested-changes state.
- Apply fixes only when the user separately requests implementation.
- Publish review comments or submit a platform review only when explicitly authorized.
- Do not weaken or inflate a priority to influence workflow.
