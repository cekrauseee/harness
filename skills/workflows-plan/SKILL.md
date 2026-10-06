---
name: workflows-plan
description: Plan a substantial change as deliverables and dependencies, whether requested alone or needed within authorized implementation.
---

# Plan

Produce a plan from the objective, relevant context and known constraints. Resolve material uncertainty within scope; keep ordinary implementation choices open to the executor. A planning-only request does not authorize implementation or delegation. When planning is a suboperation of authorized implementation, retain that broader objective and continue it after the plan.

Organize a macro plan into modules with distinct outcomes, boundaries, dependencies and completion conditions. A single table can be sufficient. Modules describe deliverables, independently of agents and branches. A solo agent can execute a modular plan; a module need not become a PR. Use semantic names that survive changes in execution topology. A mechanical edit does not require macro planning.

Store a plan that must survive the conversation in `work/<work>/README.md` in the project environment. Put module details in `modules/<module>.md` only when they need their own context. The entry point holds common constraints and references, not duplicate module explanations or live progress. Read [file contracts](references/file-context.md) when creating or changing these files; do not load unrelated team or handoff sections. This skill includes `scripts/harness.py` for location and atomic Markdown writes when needed.

Separate confirmed decisions, remaining decisions and the freedom left to implementation. Include the relevant source references rather than a copied investigation. Keep internal labels out of proposed product text and developer documentation.

Deliver the modular plan and its entry path when persisted, with material unresolved choices. Stop there for a planning-only request; otherwise resume the authorized outer task. A plan does not itself authorize agents, worktrees, commits or handoffs.
