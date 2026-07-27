---
name: harness-review
description: Review code, documentation, commits, or pull requests read-only. Use for diff review, risk assessment, or change validation that requires evidence-backed P0-P3 findings.
---

# Harness Review

Review for concrete defects and risks. Reviews are read-only by default: identify actionable findings without changing files, commits, branches, pull requests, or external state.

## Review Procedure

1. Establish the requested scope and applicable repository rules.
2. Inspect the complete relevant diff and enough surrounding code, tests, configuration, or documentation to understand behavior.
3. Verify each suspected issue. Trace inputs, control flow, affected callers, and existing tests instead of relying on pattern matching alone.
4. Classify actionable findings with [references/review-severity.md](references/review-severity.md).
5. Keep line ranges tight and ensure the cited line is part of, or directly explains, the defect.
6. Optionally validate structured findings before rendering them:

   ```bash
   python3 scripts/validate_review.py findings.json
   ```

7. Present findings in priority order. If none remain after verification, state that no actionable findings were found and mention any material verification gap.

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
