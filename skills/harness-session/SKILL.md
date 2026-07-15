---
name: harness-session
description: Start, checkpoint, inspect, or explicitly close concise project work sessions in the global Harness. Use for durable handoffs across agent hosts or worktrees, to repair automatic lifecycle state, to record the current task and next step before interruption, or to close completed continuity records.
---

# Harness Session

Maintain concise operational continuity. Hooks normally start and checkpoint sessions; use this skill for explicit handoffs, inspection, and closure.

## Start

```bash
python3 scripts/session.py --repo <repository> --json start \
  --task "Document the authentication lifecycle" \
  --branch docs/authentication-lifecycle \
  --worktree <absolute-path>
```

The returned session ID is host-neutral. Reuse it from Codex, Claude Code, or another agent.

## Checkpoint

```bash
python3 scripts/session.py --repo <repository> --json update \
  --session-id <id> \
  --summary "Mapped refresh and revocation paths." \
  --next-step "Verify the mobile fallback."
```

Summaries are capped at 4,000 characters, tasks at 500, and next steps at 1,000. Replace the summary with the current state instead of appending a transcript.

## Close

`Stop` is turn-scoped and does not close a session. Close only when work is genuinely complete or intentionally abandoned:

```bash
python3 scripts/session.py --repo <repository> --json close \
  --session-id <id> \
  --summary "Documentation merged; no remaining work."
```

Use `list --status active|closed|all` to inspect sessions.

## Rules

- Record outcomes, blockers, evidence, and the next action; omit conversation history.
- Do not create a session for work that will finish without a handoff unless hooks already created one.
- Do not close another active agent's session without evidence that its work ended.
- Do not treat a session as durable project knowledge; classify memory separately.
- Never store secrets or full tool logs.

Read [references/session-schema.md](references/session-schema.md) when building an adapter.
