# Session schema

Every session is a JSON record with an opaque UUID, task, status, timestamps, concise summary, next step, branch, worktree path, and optional host metadata.

Active records live in `sessions/active/`. Explicitly closed records move to `sessions/closed/`. A host `Stop` event updates `last_seen_at`; it does not imply task completion.

Session files are operational handoffs. Stable facts must pass through memory candidate classification or versioned documentation.
