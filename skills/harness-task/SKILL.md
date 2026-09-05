---
name: harness-task
description: Coordinate substantive work in a shared project by registering scope before writes and recording outcomes, blockers and handoffs. Use when several chats share files or work needs continuity across interruptions.
---

# Harness Task

Record the intended contribution before changing shared resources. Checkpoint a meaningful result before delivering it. A simple question needs no task. Commands are relative to this installed skill; use its absolute script path from another working directory.

## Register work

```bash
python3 scripts/harness.py task.start --project /path/to/project --data '{"objective":"Update the introduction","resources":["notes/introduction.md"],"request_id":"introduction-start"}'
```

Save the returned task and session IDs. IDs, timestamps, workspace provenance, revision and journal entries are generated together. A resource is a workspace-relative file or directory; `.` covers the workspace. Globs are rejected. A directory claim covers its descendants. Resolve conflicts shown by the command before writing overlapping resources; continue independent work where safe.

To extend your scope, use `task.claim` with your `session_id`, `resources` and a new `request_id`. To contribute to an existing task, use `task.join` with its `task_id`; each participant gets a separate session. Use `task.list` or `task.show` to inspect relevant work. Do not reuse another participant's identity simply because their session is quiet. If independent evidence establishes that a former writer stopped, record that evidence in the reason for an explicit release, then join with a new session. Age alone is insufficient.

## Persist a result

```bash
python3 scripts/harness.py task.checkpoint --project /path/to/project --data '{"session_id":"<returned-id>","summary":"Updated the introduction and checked its sources.","evidence":["notes/introduction.md; checked cited archive"],"next_action":"User acceptance remains pending.","status":"delivered","request_id":"introduction-delivery"}'
```

Use `active` for ongoing work and `blocked` for an unresolved obstacle. Both retain responsibility. `delivered` releases only this session's claims; record unresolved next actions explicitly. Delivery is not acceptance, commit or publication. No manual session closure is needed. Use `task.release` with a reason if you stop writing without delivering; join the task again for a new participant before writing again.

A checkpoint stores the outcome, evidence and next action in one transaction. Omit transcripts, hidden reasoning, secrets and routine output. After an interruption, read persisted checkpoints and inspect actual files before resuming. Inactivity signals uncertain presence; it never proves that a writer stopped.

## Resolve a follow-up

After delivery, use `task.event` with your `session_id`, `kind` (`accepted`, `committed`, `published` or `resolved`), `evidence` and a new `request_id`. Name completed follow-ups in `resolves_checkpoint_ids`; only those pending actions are cleared. The original checkpoints remain history. To reconcile an explicitly released predecessor after replacement work, name it in `resolves_session_ids` with evidence. An event without these targets records the event without guessing what it resolves. Inspect `guide` for inputs.

## Consolidate contributions

Run `consolidate` to inspect current-workspace claims and contributions. This read does not reserve the workspace. Before a stable consolidation, acquire a new task claim with `resources:["."]`, then compare the report with actual files and checks. Another writer's claim blocks that reservation, including an inactive writer. Other worktrees' results are context; they are not automatically present in this tree.

All commands return JSON; exit 2 indicates failure. On an uncertain retry, reuse the same `request_id` and identical inputs. A new action needs a new key. On revision conflict, reread relevant work and reconsider the change. Use `guide --data '{"operation":"task.checkpoint"}'` for an operation's minimum inputs.
