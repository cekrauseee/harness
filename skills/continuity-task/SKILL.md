---
name: continuity-task
description: Reserve shared project writes, preserve needed continuations, and close completed contributions.
---

# Continuity Task

Use this skill before shared project-file writes or to continue or close an existing contribution. A read-only task needs no reservation or delivery record. Commands use this installed skill's `scripts/continuity.py`; use its absolute path from elsewhere.

For new work, select an originating project and reserve the files or directories you will change:

```bash
python3 scripts/continuity.py claim --project /path/to/project --purpose "Revise introduction" --resource notes/introduction.md
```

The claim checks conflicts atomically; a preliminary survey of handoffs is unnecessary. Save the returned contribution ID and version. Each independent writer has its own contribution. Directories cover descendants and globs are rejected. Relative paths and `.` cover only the selected workspace. For work across projects, reserve the other paths absolutely; an environment does not reserve its members automatically. Extend ownership with `claim --owner <id> --expect <version> --resource <path>`. Keep the originating project selector when extending a contribution. Resolve reported overlaps before writing there; continue independent work where possible.

Use current conversation evidence while working. Publish a concise handoff when an interruption, blocker or meaningful continuation need makes it useful: outcome, evidence, remaining work and next action. Use `handoff --owner <id> --expect <version> --input -`, adding `--release` when you stop writing. Active checkpoints retain the reservation. Agent messages carry transient coordination; handoffs contain no transcripts, secrets or routine logs.

Before delivery, complete the assigned work under its applicable project and workflow requirements. Consolidate durable guidance or useful knowledge when there is any, then choose the necessary ending:

- **Complete:** after consolidation, run `finish --owner <id> --expect <version>` to atomically remove your contribution and its reservations. No final handoff is required.
- **Continuation:** publish one current handoff with `--release`. Keep it until the remaining work is completed or carried forward.

Include the originating `--project /path/to/project`, or use `--environment-id <id>` for handoffs and completion. A contribution retains its origin even when its resources span several projects. Completion needs no separate cleanup request. Remove owned temporary inputs and account for related predecessor records; preserve unrelated work. Use the existing outcome and verification evidence. Managing Continuity state adds no technical review or testing requirement.

Read [recovery.md](references/recovery.md) only for resumption, predecessor cleanup, uncertain operations or another writer's reservation. A possible future commit or publication outside the current request is not pending work. These operations grant no permission for external actions.
