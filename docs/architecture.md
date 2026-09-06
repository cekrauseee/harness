# Architecture

## Agent responsibilities

Knowledge lives in ordinary Markdown files. Agents decide what matters, search with existing file tools, read selected documents and consolidate their contents. Sources, scope, dates and uncertainty are prose, not a runtime schema. There is no lexical-ranking engine, classifier, context-budget system, duplicate detector or knowledge index to maintain.

The optional `knowledge/guidelines.md` is an agent convention for confirmed durable project guidance. [Harness Remember](../skills/harness-remember/SKILL.md#durable-project-guidance) defines its curation boundaries; Harness Recall reads it on substantive entry or resumption. It uses the same observed-content writes as any other knowledge document. The helper neither recognizes guidance nor decides its authority.

One current contribution represents a writer's purpose, workspace, reserved resources and latest handoff. The agent writes the handoff as Markdown. There are no separate sessions, checkpoint histories, acceptance graphs, execution journals or retry archives. Before final delivery, the agent consolidates useful knowledge, releases its reservations and removes completed or superseded records for that work. A genuine continuation keeps one current handoff. Unrelated records and other writers' ownership are preserved. The [delivery procedure](../skills/harness-task/SKILL.md#before-every-delivery) makes this part of completing authorized work rather than a separate user cleanup request.

The host owns execution tools, permissions and agent creation. A short host instruction supplies the lifecycle triggers; editing that instruction is ordinary authorized file work. No hooks, installer or background maintenance subsystem is required. Closing a chat runs no cleanup process: the agent verifies consolidation before replying. If execution is interrupted, remaining state must be reconciled on resumption. Separate atomic helper operations do not make that whole semantic sequence atomic or guarantee agent compliance.

## Mechanical guarantees

The single helper in `src/harness.py` uses a shared operating-system lock and atomic replacement. A resource reservation checks the requested paths and records ownership in one transaction. A final handoff and its ownership release are written in the same project snapshot, preventing an unexplained gap between the two.

Each contribution has a version for compare-and-swap updates. Knowledge reads return observed Markdown bytes and their hash together. Writes/deletions check that hash under the lock. An identical intended write can be retried without retaining old responses; different stale writes fail and require reconciliation. The helper does not judge the text or establish completion. The agent must assess the result against the actual objective and evidence.

Identity and coordination share a small `project.json`; knowledge files are independent. This avoids a second index or a multi-file delivery transaction. Git worktrees share identity through their physical common directory; regular folders use registered roots. Unknown identity changes require explicit binding. Reference-only projects can have no working roots.

Reservations are cooperative and never expire based on age. The helper requires local POSIX locking and atomic filesystem replacement. It cannot guarantee the behavior of a writer that ignores the protocol or edits stored metadata directly.

## Why scripts remain

The runtime helper prevents races and partial persistence that agent instructions alone do not prevent. It contains only those mechanical operations. The source-copy script exists because selective skills installation must work without the repository. The installation verification script exercises that actual distribution boundary in disposable homes. Neither development script is part of the agent's normal workflow.

Each installed Harness skill gets a generated copy of the one helper. There is no shared package installation, paid API, daemon, model coupling or old-format compatibility layer.
