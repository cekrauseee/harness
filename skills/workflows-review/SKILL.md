---
name: workflows-review
description: Review an identified code change for actionable defects or requested code-design feedback, not general product strategy.
---

# Review

Identify the requested scope, criteria, target version and comparison base. Review a stable, identifiable version; a parallel implementation can advance through later review rounds. Do not create commits merely to manufacture a review target. For uncommitted changes, use a preserved snapshot or identified patch consistent with the request.

Inspect the changed code in scope and dependencies needed to assess behavior, reusing available evidence. A focused review does not require reviewing unrelated changes or rerunning the executor's entire verification. For correctness findings, establish a reachable trigger, concrete impact and precise file/line evidence. Use the host severity scheme where required; otherwise P0 is catastrophic, P1 urgent, P2 ordinary correctness/reliability and P3 localized low risk.

Report actionable findings and a correction direction. Distinguish defects from requested design recommendations. Apply the user's testing policy and project requirements when assessing evidence; missing tests are not automatically a defect without a concrete uncovered risk or required check. Do not demand tests for every function or cosmetic detail. If no findings remain, say so without claiming unexamined behavior is correct. Include material verification gaps.

Source review is read-only unless implementation is also requested. When persistent findings are part of the assignment, write them to the review front's `findings.md`, tied to the reviewed version; do not reproduce them in the module and plan. This skill includes `scripts/harness.py` for atomic context writes. Read [file contracts](references/file-context.md) only if a persistent review front must be established or changed.

Deliver the review result and continue any broader authorized task. Applying corrections, remote comments, approvals and requested-changes states require their corresponding authorization. A new review round is driven by the request or meaningful changes, not an automatic loop.
