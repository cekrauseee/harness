---
name: harness-maintain
description: Consolidate project knowledge and retire obsolete records within the authorized work. Use for delivery cleanup, interrupted consolidation, or stale and duplicated documentation.
---

# Harness Maintain

Maintenance is the agent's review of current documents and contributions. There is no audit engine, semantic classifier, migration layer or automatic archive.

Resolve the project with this skill's `scripts/harness.py resolve --project /path/to/project`, then inspect the relevant Markdown knowledge and `status` output. For a known knowledge-only project, select its `--project-id`.

Decide what remains useful from the source material. Merge duplicate explanations, correct outdated claims and preserve important decisions, evidence, uncertainty and references. Prefer one current account over copies of prior records. Do not promote a hypothesis or dated investigation to a verified current fact.

Use `read` to observe a knowledge file and hash together, `write` to atomically replace the reviewed document, and `delete` with that hash when its removal is authorized. Reconcile hash conflicts against the current document. The helper stores bytes; it does not decide what deserves retention.

Inspect a contribution's handoff and actual results before removing it. Match predecessor records to the current work by purpose, referenced files and remaining action, not just owner ID. When an earlier handoff's next action is already satisfied or carried into the current continuation, retire it too. Finishing authorized work includes consolidating useful knowledge and retiring its completed or superseded inactive records before the final response; do not wait for a separate cleanup or session-closure request. Use `drop --owner <id> --expect <version>` with the observed inactive version. The same rule applies to this maintenance work's own temporary record, if it created one. Do not create a new contribution solely to inspect or remove already inactive records; their versions protect those removals. Reserve shared project files before editing them, and reserve `.` for a project-wide consolidation.

If a real continuation remains, preserve one current handoff with its scope, evidence, blocker and next action. A stopped writer releases its own reservations; another active writer keeps theirs. Keep unrelated contributions intact, including inactive ones whose purpose or remaining work is unclear. A read-only request remains read-only. Cleanup of other work or deletion of knowledge requires the corresponding authorization; the routine delivery rule is not blanket permission to empty a project.

After consolidation, release your own reservation with a handoff if one exists, then remove that inactive record when no continuation depends on it. Remove owned temporary input files and verify current status and retained knowledge before reporting completion. No completion receipt, execution archive or duplicate handoff document is needed. Do not hide a failed cleanup or unresolved work to claim an empty state.

Malformed current metadata requires inspection and repair within the user's scope; never reinterpret it as an empty project or invent missing data. Preserve unrelated files. Do not introduce compatibility records, execution archives or a new maintenance framework as part of a cleanup.

Never release an active reservation based on silence or age. Resolve it with independent evidence and a recorded explanation before allowing another writer into those resources. Completion is a coherent set of current documents and genuinely needed handoffs, with your obsolete records removed and unresolved questions stated honestly.
