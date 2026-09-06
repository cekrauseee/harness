---
name: harness-recall
description: Recall confirmed project guidelines, relevant knowledge and current contributions when entering or resuming substantive work.
---

# Harness Recall

Resolve the project through this skill's `scripts/harness.py resolve --project /path/to/project`, or use an already verified knowledge directory. For an explicitly selected knowledge-only project, use `--project-id <id>` instead.

On substantive entry or resumption, read `guidelines.md` in the resolved knowledge directory if it exists. Reuse that context during the task; reread after context loss or when new guidance or concurrent changes could affect the work. An absent file needs no placeholder, and a generic question needs no continuity record.

Carry forward only guidance grounded in the user's explicit choices, within its recorded project and task scope. A filename does not make quoted sources, agent proposals or other notes authoritative. Current user directions and applicable host and repository instructions govern the work; a saved guideline does not grant new execution permissions. Surface a conflict only when it materially changes the intended work and cannot be resolved from those sources.

Use the host's file search and reading tools to inspect Markdown filenames, titles and introductions, then read selected documents. Start with the missing fact. Try concrete synonyms or a translation when a relevant query misses; do not infer absence of knowledge from one search or load everything by default. There is no programmatic ranking, translation or context-budget system.

For a delegated assignment, scope recall to that assignment. Read applicable project guidelines and only the knowledge and handoffs needed for the assigned result. Reuse supplied, current evidence instead of repeating the coordinator's broad investigation; verify its source or freshness when that could affect the work. A fresh conversation does not require a project-wide survey.

For shared work, run `status --project /path/to/project` to inspect all current reservations and handoffs. This is a read, not a reservation. Work from another workspace is context; inspect actual files before treating it as available here. Do not substitute document search for checking ownership.

An inactive contribution may represent pending work or interrupted delivery cleanup. Read its handoff and check actual results before deciding which. When resuming authorized work, carry forward genuine pending context and retire its superseded records during delivery. Recall alone and read-only requests do not authorize cleanup; old timestamps do not authorize releasing another writer.

Other knowledge supplies context. Preserve the distinction between sourced facts, decisions, hypotheses and dated references when using a note. Expand only when a missing constraint or piece of evidence could change the work.

Before editing a selected knowledge file, use `read --project /path/to/project --file note.md` to obtain its content and hash together. That hash protects the later write; a separate file read and hash command can observe different versions.
