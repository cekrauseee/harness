---
name: review
description: "Review an identified code change for concrete, actionable defects tied to the reviewed version. Use when asked to review a diff, branch, commit or pull request. Not for applying fixes, which is implement, or product discussion."
---

# Review

Establish the scope, the criteria, the target version and the comparison base, then review that stable version: a commit, branch, tag, pull request or preserved snapshot. Create no commits merely to obtain a target; a parallel implementation can advance and be reviewed in a later round.

Inspect the changed code in scope and the dependencies needed to assess its behavior, reusing available evidence; a focused review does not rerun the executor's whole verification. For each correctness finding establish a reachable trigger, the concrete impact and precise file and line evidence. Use the host's severity scheme where one exists; otherwise P0 catastrophic, P1 urgent, P2 ordinary correctness or reliability, P3 localized low risk.

Report actionable findings with a correction direction, separating defects from requested design feedback. Apply the user's testing policy when judging evidence: missing tests are a defect only for a concrete uncovered risk or a required check. When nothing remains, say so without claiming unexamined behavior is correct, and state material verification gaps.

Review is read-only unless corrections are also requested. When persistent findings are part of the assignment, write them to the review front's `findings.md` tied to the reviewed version instead of repeating them in the plan or module. `scripts/harness.py` in this skill, run by its absolute path, writes Markdown atomically with `write --expect <observed-sha256-or-missing>`; read [file contracts](references/file-context.md) only if a persistent review front must be created.

Deliver the result and continue any broader task that requested it. Applying corrections, posting remote comments, approving or requesting changes are separate requests; a new round follows a request or meaningful changes, not an automatic loop.
