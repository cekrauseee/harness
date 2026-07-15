# Review Severity

## Priority Levels

| Priority | Meaning |
| --- | --- |
| `P0` | A certain release or operation blocker with catastrophic data loss, broad compromise, or equivalent critical impact. Stop affected work. |
| `P1` | A major correctness, security, or regression risk that should be resolved urgently. |
| `P2` | A relevant correctness, reliability, or maintainability defect that should be fixed in normal work. |
| `P3` | A localized, low-risk defect that is still concretely worth fixing. |

Priority combines impact, likelihood, and affected scope. A theoretical possibility without a plausible execution path is not a finding.

## Evidence Requirements

A finding must establish:

1. the input, state, or action that reaches the defect;
2. the code or documentation behavior that causes it;
3. the user, system, developer, or operational impact;
4. why existing guards or tests do not prevent it.

Do not report style-only differences unless they violate an explicit rule and cause concrete harm. Do not combine unrelated defects under one title.

## Ordering

Order findings by priority, then by the strength and breadth of impact. State `No actionable findings.` when the verified set is empty. Add residual risks or unrun checks separately; do not invent a low-priority finding to fill the review.
