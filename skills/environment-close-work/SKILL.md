---
name: environment-close-work
description: Consolidate useful knowledge and remove temporary context for a completed work item.
---

# Close work context

Close the internal material of a completed work item, not the environment, checkout or chat. Start with the named work and sufficient evidence that its requested objective is complete. Finishing a module, a review round or one agent's participation does not establish that the entire work is complete.

Reuse the existing result and verification evidence. Preserve material still needed by active fronts, pending handoffs or other work. Resolve those consumers or leave the work open; do not infer completion from age, a quiet chat or an agent ID. Consolidate confirmed, useful durable knowledge into `knowledge/<subject>.md` when there is any. Existing canonical knowledge needs no duplicate summary.

Once the whole work can be removed, use this skill's helper by absolute path:

```bash
python3 scripts/harness.py inspect-work --environment /path/to/environment --work access-control
python3 scripts/harness.py close-work --environment /path/to/environment --work access-control --expect <observed-sha256>
```

The hash protects against intervening file changes. The helper cannot decide whether a handoff has been consumed or a front is finished; that decision belongs to the agent using current evidence. It removes only `work/<name>/`, without an archive or receipt. A conflict requires inspecting the changed material, not forcing deletion. An interrupted cleanup can be retried for the same work; preserve both paths if the name was reused.

Report completion or the remaining consumer that prevents it. Worktree removal, branch deletion, commit, publication and chat archival retain their separate scope and authorization.
