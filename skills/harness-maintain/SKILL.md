---
name: harness-maintain
description: Consolidate project knowledge and remove explicitly authorized obsolete material. Use when documentation is stale, duplicated or unclear, or current contribution records need cleanup.
---

# Harness Maintain

Maintenance is the agent's review of current documents and contributions. There is no audit engine, semantic classifier, migration layer or automatic archive.

Resolve the project with this skill's `scripts/harness.py resolve --project /path/to/project`, then inspect the relevant Markdown knowledge and `status` output. For a known knowledge-only project, select its `--project-id`.

Decide what remains useful from the source material. Merge duplicate explanations, correct outdated claims and preserve important decisions, evidence, uncertainty and references. Prefer one current account over copies of prior records. Do not promote a hypothesis or dated investigation to a verified current fact.

Use `read` to observe a knowledge file and hash together, `write` to atomically replace the reviewed document, and `delete` with that hash when its removal is authorized. Reconcile hash conflicts against the current document. The helper stores bytes; it does not decide what deserves retention.

Inspect a contribution's handoff before removing it. Consolidate any useful knowledge first, then use `drop --owner <id> --expect <version>` for an authorized inactive entry. Do not release an active reservation based on silence. Reconcile it with evidence and a recorded explanation before allowing another writer into those resources.

Malformed current metadata requires inspection and repair within the user's scope; never reinterpret it as an empty project or invent missing data. Preserve unrelated files. Do not introduce compatibility records, execution archives or a new maintenance framework as part of a cleanup.

Completion is a smaller, coherent set of current documents and useful handoffs, with obsolete material removed and unresolved questions stated honestly.
