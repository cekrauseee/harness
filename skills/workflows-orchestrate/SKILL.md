---
name: workflows-orchestrate
description: Configure and coordinate explicitly authorized agent work and continue an existing team.
---

# Orchestrate

Orchestrate when requested or when continuing an authorized team. The coordinator owns the overall objective, responsibilities, dependencies, priorities and acceptance of delivered outcomes. Executors own technical investigation, implementation, integration, verification and fixes. Manage outcome gaps instead of working operationally alongside executors or auditing their implementation after delivery.

Use the plan's modules without making the tree mirror them. A front may handle several modules, and implementation and review fronts may reference the same module. Assign coherent outcomes with relevant constraints and direct context paths. Give each executor its own front/module entry, not the entire team history. Executors do not delegate further unless that is part of their authorization.

Keep the concrete team's configuration in `work/<work>/team.md`: logical names, roles, front references, relationships and requested model/effort or other relevant settings. Distinguish intended configuration from actual host-created agents. Record native IDs after creation when needed to contact or resume them; an ID does not establish live status. Configuration can be prepared without spawning. Honor explicit choices, supported host parameters and cost constraints; avoid unintentionally inheriting a more expensive coordinator configuration.

Read [file contracts](references/file-context.md) when establishing the team or its fronts. This skill includes `scripts/harness.py` for location and atomic context writes. Keep the current responsibility, workspace and continuation in each front's `context.md`; do not mirror status in the plan or team file. One front owns writes to a workspace; a pair coordinates alternation without claims or per-action bookkeeping. Independent writing fronts use separate worktrees inside the environment.

Dispatch only authorized work, reuse workers for related follow-up and wait for meaningful results. Trust their technical verification. Accept outcomes against the assignment; return specific missing, contradictory or incomplete results to an executor. Independent technical review is added only when required or requested. Review fronts use identified versions.

Update context at useful changes of responsibility, direction or result. Finish when the overall objective is delivered and known outcome gaps are resolved. Do not add technical audit loops, transcript collection or repeated checks. Report remaining limitations honestly; delegation grants no additional permissions.
