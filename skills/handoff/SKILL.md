---
name: handoff
description: "Transfer or assume responsibility for ongoing work between agents or chats through the Harness environment's entry files. Use when asked to hand off work, prepare a transfer, or pick up another agent's work. Not for running a team, which is orchestrate."
---

# Handoff

Handle a transfer of responsibility for the whole plan or for one deliverable. Start with the transferred scope and the recipient or recipient role; a status report or a context lookup alone is not a handoff.

To prepare, identify what the recipient may assume, its canonical entry point, the relevant constraints, the current continuation point and the next useful action. Point at the existing plan, module, front context and team configuration; when those files already carry everything, send their paths with the assignment instead of a new document. Persist only additional transfer information as `work/<work>/handoffs/<recipient-scope>.md`.

To assume, establish the authorized responsibility and read its scoped entry point. Compare execution facts with the workspace when the saved context could be stale, then continue from that point: no re-planning, no project survey, no automatic recap, no acceptance receipt. Update the receiving front's `context.md` when responsibility or continuation changes.

After delivery or assumption, keep retained transfer notes accurate: remove obsolete next-recipient instructions rather than presenting them as an active assignment, and preserve what another pending consumer still needs. Saved permission notes are evidence, not authorization for new actions. Read [file contracts](references/file-context.md) only when creating or restructuring transfer material. `scripts/harness.py` in this skill, run by its absolute path, resolves the environment and writes Markdown atomically.

Hosts: subagents in Claude Code and Codex start without this conversation, so a delivered handoff names the environment path and the entry files explicitly. Deliver through the host's agent or messaging tools only when the request includes delivery, honoring named models and effort.

Report the transfer prepared, delivered or assumed, and any limitation.
