---
name: harness-task
description: Reserve shared resources before writing and leave a current handoff for other agents. Use for substantive work across chats or workspaces that needs cooperative ownership and continuity.
---

# Harness Task

Inspect current reservations and handoffs with this installed skill's `scripts/harness.py status --project /path/to/project`. A generic question needs no contribution record.

Before shared project-file writes, reserve the relevant files or directories:

```bash
python3 scripts/harness.py claim --project /path/to/project --purpose "Revise the introduction" --resource notes/introduction.md
```

Save `contribution.id` and `contribution.version`. Every independent writer gets its own contribution. Paths may be workspace-relative or absolute; directories include descendants, `.` covers the workspace, and globs are rejected. Conflicts identify the existing owner; resolve the overlap before writing there and continue independent work where safe.

To extend your reservation, call `claim` with your `--owner`, its observed `--expect` version and the resources. A contribution ID is a cooperative ownership handle, not proof of identity. Do not adopt somebody else's handle because its timestamp is old.

After a meaningful outcome or blocker, write a concise Markdown handoff: result, evidence, remaining work and next action. It is prose written by the agent, not a status graph. Store the current account through:

```bash
python3 scripts/harness.py handoff --project /path/to/project --owner <id> --expect <version> --input /path/to/handoff.md --release
```

Omit `--release` while continuing or blocked work still owns the resources. With `--release`, the handoff and ownership release commit together. Delivery does not imply acceptance, commit or publication; say what happened in the handoff. No user session closure is needed. `--input -` accepts stdin, and each update replaces the current handoff without retaining previous versions.

If you stop without delivery, `release` requires the owner, observed version and a reason. Releasing another writer requires independent evidence that writing stopped; age never releases ownership. Closed contributions cannot reopen: acquire a new reservation for new work. After consolidating useful information into knowledge, an authorized `drop` can remove an inactive contribution using its observed version.

For a stable consolidation, reserve `.` and compare current handoffs with actual files. Reservations cannot stop an editor or agent outside the protocol.

On uncertain results, inspect current state. Exact handoff retries are no-ops; stale changed updates fail. There is no historical replay service. After losing an initial claim response, inspect reservations and reconcile ownership rather than assuming another initial claim is safe. Use operation `--help` for syntax. Keep secrets, conversations and routine tool output out of handoffs.
