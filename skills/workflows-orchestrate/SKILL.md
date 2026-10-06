---
name: workflows-orchestrate
description: Coordinate an explicitly requested team or continue authorized multi-agent work toward delivered outcomes.
---

# Orchestrate

Orchestrate when requested or when continuing an authorized team. The coordinator owns the overall objective, responsibilities, dependencies, priorities and acceptance of delivered outcomes and evidence. Executors own technical investigation, implementation, integration, verification and fixes. Apply the user's coordination policy; normally return concrete gaps to the responsible executor. Targeted inspection or checks can resolve a contradiction or integration gap when permitted, but do not routinely repeat the executor's work or interfere with an active writer.

Use the plan's modules without making the tree mirror them. A front may handle several modules, and implementation and review fronts may reference the same module. Assign coherent outcomes with relevant constraints and direct context paths. Give each executor its own front/module entry, not the entire team history. Executors do not delegate further unless that is part of their authorization.

A short collaboration can use native messages and results without persistent team or front files. When shared coordination or continuation needs persistence, keep the concrete team's configuration in `work/<work>/team.md`: logical names, roles, front references, relationships and requested model/effort or other relevant settings. Distinguish intended configuration from actual host-created agents. Record native IDs when useful for continuation; an ID does not establish live status. Configuration can be prepared without spawning. Honor explicit choices, supported host parameters and cost constraints; avoid unintentionally inheriting a more expensive coordinator configuration.

Read [file contracts](references/file-context.md) when creating persistent team or front structure. This skill includes `scripts/harness.py` for location, initialization when useful context first needs storage, and atomic context writes. When fronts need records, keep current responsibility, workspace and continuation in their `context.md`; do not mirror status in the plan or team file. One front owns writes to a workspace; a pair coordinates alternation without claims or per-action bookkeeping. Independent writing fronts use separate worktrees inside the local environment.

Dispatch only authorized work, reuse workers for related follow-up and wait for meaningful results. Reuse their technical verification and assess its relevance to the delivered outcome. Return specific missing, contradictory or incomplete results to an executor. Independent technical review follows the applicable policy and authorization. Review fronts use identified versions.

Update context at useful changes of responsibility, direction or result. Finish when the overall objective is delivered and known outcome gaps are resolved. Do not add technical audit loops, transcript collection or repeated checks. Report remaining limitations honestly; delegation grants no additional permissions.
