---
name: harness-session
description: Maintain concise episodic project handoffs. Use when material work may cross interruptions, hosts, or workspaces; when a current handoff needs inspection or repair; or when work becomes dormant or complete.
---

# Harness Session

Maintain concise operational continuity without storing a transcript. Create a session lazily only when material work may need a future handoff.

## Start

```bash
python3 scripts/session.py --project <project-path> --json start \
  --title "Authentication lifecycle documentation" \
  --task "Document the authentication lifecycle" \
  --read-when "when continuing authentication documentation" \
  --tag authentication \
  --tag documentation \
  --branch docs/authentication-lifecycle \
  --worktree <absolute-path>
```

The returned session ID is host-neutral. Reuse it from Codex, Claude Code, or another agent.

## Checkpoint

```bash
python3 scripts/session.py --project <project-path> --json update \
  --session-id <id> \
  --summary "Mapped refresh and revocation paths." \
  --next-step "Verify the mobile fallback."
```

Tasks are capped at 1,000 characters. A starting summary is capped at 1,000 characters; later summaries are capped at 4,000. Next steps are capped at 1,000. Replace the summary with the current state instead of appending a transcript.

## Dormant or close

Mark interrupted but still relevant work dormant. Close only when work is genuinely complete or intentionally abandoned:

```bash
python3 scripts/session.py --project <project-path> --json dormant \
  --session-id <id> \
  --summary "Waiting for the approved source material."

python3 scripts/session.py --project <project-path> --json close \
  --session-id <id> \
  --summary "Documentation merged; no remaining work."
```

Use `list --status active|dormant|closed|all` to inspect sessions. `--repo` remains a compatibility alias for `--project`.

## Rules

- Record outcomes, blockers, evidence, and the next action; omit conversation history.
- Do not create a session for work that will finish without a handoff.
- Keep one current active handoff; mark paused work dormant instead of leaving empty active sessions.
- Do not close another active agent's session without evidence that its work ended.
- Do not treat a session as durable project knowledge; classify memory separately.
- Never store secrets or full tool logs.

Read [references/session-schema.md](references/session-schema.md) when building an adapter.
