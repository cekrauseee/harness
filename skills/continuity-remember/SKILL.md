---
name: continuity-remember
description: Preserve confirmed durable guidance, record reusable project knowledge, or correct existing knowledge.
---

# Continuity Remember

Retain information that will help a future task and is not already adequately captured in a canonical source. Routine progress, facts readily recovered from current code and completion receipts need no note. A read-only request remains read-only.

Reuse a known destination or search the relevant subject before adding a document. Keep developer documentation in the repository; external knowledge may retain context or a short pointer to it. Write concise Markdown with a clear title, scope and source. Environment knowledge is shared: identify which project or cross-project relationship the note concerns. Distinguish confirmed choices, facts, hypotheses and dated evidence. Consolidate duplicate or superseded content within the authorized subject rather than accumulating records.

When the user establishes lasting project guidance, update `guidelines.md` without a separate save request. Record its scope and brief confirmation source. Keep ambiguous or one-time directions local to the task; clarify only when the distinction affects the requested work. Rules that must apply to every task belong in applicable host or repository instructions, not solely in optional recall. Preserve user scope when choosing that destination. Stored guidance never authorizes future actions.

Resolve storage with this skill's `scripts/continuity.py resolve --project /path/to/project`, or reuse the verified location. Observe the selected file and hash together before a protected update:

```bash
python3 scripts/continuity.py read --project /path/to/project --file note.md
python3 scripts/continuity.py write --project /path/to/project --file note.md --input - --expect <hash>
```

Supply the revised Markdown on stdin, or give an input file. Use `missing` only after confirmed absence. Reconcile conflicting content rather than substituting a new hash blindly. Use `delete --file note.md --expect <hash>` to remove a note whose useful content has been consolidated and whose deletion is within scope. Environment-wide selection uses `--environment-id <id>`.

Finish with useful current knowledge, accurate sources and no owned temporary input files. Omit secrets, transcripts, private reasoning and execution logs.
