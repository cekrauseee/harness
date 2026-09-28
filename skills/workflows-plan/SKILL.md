---
name: workflows-plan
description: Create or revise a modular macro plan with concrete deliverables and dependencies.
---

# Plan

Produce a plan from the objective, relevant context and known constraints. Resolve material uncertainty within scope; keep ordinary implementation choices open to the executor. Planning does not authorize implementation or delegation.

Always organize a macro plan into modules with distinct outcomes, boundaries, dependencies and completion conditions. Modules describe deliverables, independently of agents and branches. A solo agent can execute a modular plan; a module need not become a PR. Use semantic names that survive changes in execution topology.

Store a plan that must survive the conversation in `work/<work>/README.md` in the project environment. Put module details in `modules/<module>.md` only when they need their own context. The entry point holds common constraints and references, not duplicate module explanations or live progress. Read [file contracts](references/file-context.md) when creating or changing these files; do not load unrelated team or handoff sections. This skill includes `scripts/harness.py` for location and atomic Markdown writes when needed.

Separate confirmed decisions, remaining decisions and the freedom left to implementation. Include the relevant source references rather than a copied investigation. Keep internal labels out of proposed product text and developer documentation.

Deliver the modular plan and its entry path, with material unresolved choices. Stop at the requested planning result. A plan does not create agents, worktrees, commits or handoffs unless those actions were also requested.
