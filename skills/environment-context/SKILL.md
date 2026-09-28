---
name: environment-context
description: Retrieve missing project knowledge or the scoped context needed to resume work.
---

# Environment context

Start from the concrete information gap or supplied continuation path. Reuse context already available and still valid; a new turn or chat does not require a project survey.

When the environment location is missing, resolve it with this skill's `scripts/harness.py resolve --project /path/to/project`. Read the relevant file directly. Use the environment README only when navigation or local policy is missing. Search narrowly in `knowledge/` or the named `work/<name>/`; exclude `worktrees/` from context searches.

For a resumed assignment, begin with its `fronts/<front>/context.md` or the supplied module/handoff. Read referenced module details and dependencies only when needed. Check the relevant checkout or revision when saved context could be stale; files describe intent and continuation, while Git and the host establish current execution facts. A native agent ID does not prove the agent is running.

Return the needed facts, their source paths and unresolved gaps. Retrieval does not assume a transferred role, rewrite context, create a recap or require a handoff. If the request is to receive a transfer, establish the authorized responsibility as part of that request; lookup alone is not acceptance. Stop once the gap is resolved.
