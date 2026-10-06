---
name: environment-close-work
description: Close completed work context after preserving useful knowledge, retained deliverables and pending consumers.
---

# Close work context

Close the internal material of a completed work item, not the environment, checkout or chat. Start with the named work and sufficient evidence that its requested objective is complete. Finishing a module, a review round or one agent's participation does not establish that the entire work is complete.

Reuse the existing result and verification evidence. Preserve material still needed by active fronts, pending handoffs or other work. Resolve those consumers or leave the work open; do not infer completion from age, a quiet chat or an agent ID. Consolidate confirmed, useful durable knowledge into `knowledge/<subject>.md` when there is any. Existing canonical knowledge needs no duplicate summary.

Inspect the entire work directory, including non-Markdown outputs. Before cleanup, move or copy each retained deliverable to an appropriate durable destination outside that work subtree, verify its contents and update references used by its consumers. A derived view should identify its maintained source; an original HTML or other artifact need not be regenerable. Do not create an archive of temporary context or invent a global artifact taxonomy. If retention or the destination remains unresolved, preserve the work and report that specific issue.

Use this skill's helper by absolute path. Inspect before deciding what can be removed, then obtain a fresh hash after preservation and reference updates:

```bash
python3 scripts/harness.py inspect-work --environment /path/to/environment --work access-control
python3 scripts/harness.py close-work --environment /path/to/environment --work access-control --expect <observed-sha256>
```

The hash protects against intervening file changes. The helper lists and hashes all file types but its document read/write commands accept Markdown only; use appropriate file tools for other outputs. It cannot decide whether a handoff has been consumed, a front is finished or an artifact should be retained. It removes all contents of `work/<name>/`, without an archive or receipt. A conflict requires inspecting the changed material, not forcing deletion. An interrupted cleanup can be retried for the same work; preserve both paths if the name was reused.

Report completion or the remaining consumer that prevents it. Worktree removal, branch deletion, commit, publication and chat archival retain their separate scope and authorization.
