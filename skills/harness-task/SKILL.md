---
name: harness-task
description: Coordinate shared writes and complete delivery with consolidated knowledge and cleaned execution records. Preserve a current handoff when work remains.
---

# Harness Task

Inspect current reservations and handoffs with this installed skill's `scripts/harness.py status --project /path/to/project`. Identify any predecessor handoff for the work you are taking on and keep its ID for delivery consolidation. Match by purpose, referenced files and remaining action; a different owner ID does not by itself make an inactive handoff unrelated. A generic question needs no contribution record.

Before shared project-file writes, reserve the relevant files or directories:

```bash
python3 scripts/harness.py claim --project /path/to/project --purpose "Revise the introduction" --resource notes/introduction.md
```

Save `contribution.id` and `contribution.version`. Every independent writer gets its own contribution. Paths may be workspace-relative or absolute; directories include descendants, `.` covers the workspace, and globs are rejected. Conflicts identify the existing owner; resolve the overlap before writing there and continue independent work where safe.

To extend your reservation, call `claim` with your `--owner`, its observed `--expect` version and the resources. A contribution ID is a cooperative ownership handle, not proof of identity. Do not adopt somebody else's handle because its timestamp is old.

While working, keep a concise current handoff after meaningful outcomes or blockers: result, evidence, remaining work and next action. It is prose written by the agent, not a status graph. Use `handoff` without `--release` while actively continuing to use the reservation. `--input -` accepts Markdown on stdin; each update replaces the previous account.

Use agent messages for transient coordination and immediate dependencies. Persist a handoff when a meaningful result or blocker changes what another agent needs to continue, not for every message, tool call or unchanged status. Keep one current account with concise evidence references; do not copy the conversation. This does not replace each independent writer's reservation or the delivery procedure below.

## Before every delivery

Complete this work before the final response, without waiting for the user to say the session is over. Finishing authorized work includes retiring its temporary coordination records; no separate cleanup request is needed. An explicitly read-only request does not authorize maintenance writes or a new contribution.

1. Compare the result with the actual files and requested scope. Consolidate useful findings or confirmed guidance into the appropriate current document. Keep canonical project documentation in the repository and additional knowledge outside it. Read a knowledge note with `read --file note.md` before `write --file note.md --input FILE --expect HASH`; use the returned hash or the confirmed `missing` marker. Do not preserve execution logs, completion receipts or copies of handoffs as knowledge merely to delete their originals.
2. Publish a final current handoff and release your reservations together:

```bash
python3 scripts/harness.py handoff --project /path/to/project --owner <id> --expect <version> --input /path/to/handoff.md --release
```

3. When no real continuation depends on that handoff, remove the inactive contribution using its **returned** version:

```bash
python3 scripts/harness.py drop --project /path/to/project --owner <id> --expect <released-version>
```

Revisit the predecessor handoffs identified on entry: when their remaining action is now satisfied by your result or fully carried into the one current continuation, remove those inactive records with their observed versions too. Deleting only your newly created record is insufficient if an older handoff still describes this same completed work. This includes a record created solely for cleanup. Keep unrelated contributions intact; a shared project need not have an empty contribution list.

4. Remove temporary input files you created and no longer need. Read `status` again and verify the relevant documents and actual files. Your completed work must leave no reservation or obsolete contribution of its own. Checking completion must not create another record. Do not report clean delivery if consolidation, release or removal failed; reconcile the observed state or report the specific remaining issue.

If requested work remains blocked, deferred or handed to another writer, retain one current handoff describing what remains, the evidence and the next action. Release your reservations when you stop writing; another active writer retains theirs. Replace superseded handoffs rather than accumulating a history. A possible future commit or publication outside the current request does not by itself require retaining a contribution, and delivery grants no new permission for those actions.

## Interrupted work and shared state

On resumption, inspect current files and the relevant handoff before continuing. If an earlier delivery released its record but stopped before consolidation or removal, finish that cleanup within the authorized work. Closed contributions cannot reopen: acquire a new reservation for new writes and retire a predecessor only after its useful context is carried forward.

If you must stop without a handoff, `release` requires the owner, observed version and a reason. Releasing another writer requires independent evidence that writing stopped; age never releases ownership. Project-wide consolidation requires reserving `.` and inspecting actual files; ordinary delivery cleanup stays within the work you own. Reservations cannot stop an editor or agent outside the protocol.

On uncertain results, inspect current state. Exact handoff retries are no-ops; stale changed updates fail. There is no historical replay service. After losing an initial claim response, inspect reservations and reconcile ownership rather than assuming another initial claim is safe. Use operation `--help` for syntax. Keep secrets, conversations and routine tool output out of handoffs.
