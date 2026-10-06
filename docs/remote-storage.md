# Remote storage boundary

Harness currently uses local files and path-based project bindings. This document describes requirements for a separate future file service accessed through MCP, not an implemented interface or a second storage backend. No endpoint names, provider, schemas or migration procedure are defined here.

## Project identity and local execution

A shared project needs a stable identity independent of checkout paths, machine names and display names. Each machine explicitly associates its local checkout with that identity. Linked Git worktrees share the association; matching repository names or remote URLs must not silently combine unrelated clones or forks. Separate projects reference each other explicitly rather than sharing all context.

For example, two machines can associate their different checkout roots with the same explicitly selected shared project and retrieve the same context. A fork remains separate unless deliberately associated. References to source files identify the project and repository-relative path, plus a revision when validity depends on it; each machine resolves them against its own checkout. Absolute execution paths remain local facts.

Checkouts and worktrees remain local execution resources. Remote context storage does not need to contain them. Adopting the service will require an explicit local worktree-location policy compatible with the host; the current local helper continues to require worktrees inside its environment until that change is implemented.

## File guarantees

The service must provide authenticated, project-scoped access and durable writes with confirmed results. Updates and removals must detect changes against the observed revision instead of silently overwriting another writer. Retries after confirmed operations must be safe; an uncertain outcome must be inspectable before retrying or reporting success. Multi-file guarantees must be stated explicitly rather than inferred from per-file atomicity.

Required context or retained artifact formats must be confirmed against the actual service interface. Missing access, unavailable storage or unconfirmed writes are reported as such; they do not authorize creating a competing local source of truth. The agent decides relevance, completion and retention. Storage permissions grant access to files, not authority to implement, delegate, publish or provision services. Context never stores secrets, raw conversations or reasoning traces.

## Integration boundary

Implementation requires the real service interface, authorized access and explicit project associations. Bind the actual supported tools in plugin metadata, adapt the affected skills and references, and deliberately replace obsolete access paths. Do not add a speculative adapter, implicit fallback, compatibility layer or automatic migration now. Preserve existing environments and active consumers through any separately scoped transition.

Completion requires using the real service from two different checkout roots, resolving references locally, rejecting stale concurrent writes, handling retries and missing access honestly, and using a local worktree without remote path assumptions. Local unit tests or an unconnected mock cannot establish those outcomes. Building, hosting and operating the service are separate from Harness.
