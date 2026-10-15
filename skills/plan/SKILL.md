---
name: plan
description: "Plan a substantial change as modules with outcomes, dependencies and completion conditions, kept in the Harness environment when it must outlive the conversation. Use when asked for a plan, or when authorized implementation needs one first."
---

# Plan

Produce a modular plan from the objective, the relevant context and the known constraints. Resolve material uncertainty within the scope and leave ordinary implementation choices to the executor. A mechanical edit needs no macro plan.

Organize the plan into modules with distinct outcomes, boundaries, dependencies and completion conditions; a single table is often enough. Modules are deliverables, independent of agents, branches and pull requests: one agent can execute a modular plan, and a module need not become a PR. Use semantic names that survive changes in who executes what. Separate confirmed decisions, remaining decisions and the freedom left to implementation, and reference sources instead of copying an investigation. Keep internal labels out of product text and developer documentation.

When the plan coordinates several fronts or carries risks worth proving, give them stable ids: an `## Attention points` table of `ap-` ids with category, severity, scenario, expected handling, proof (test, qa or review) and owner module, and a `## Flows` table of `fl-` ids with actor, trigger, outcome and modules. Each module lists the ids it owns; executors may add ids, never drop one. Record `Map: yes` or `Map: no` with its reason by the objective criteria. The table format and criteria are in [execution records](references/records.md#plan); do not restate them in the plan.

Persist a plan that must survive the conversation as `work/<work>/README.md` in the project environment, with module details in `modules/<module>.md` only when a module needs its own context. The README holds the objective, shared constraints, modules and references, not live progress. Read [file contracts](references/file-context.md) when creating or restructuring these files. `scripts/harness.py` in this skill, run by its absolute path, resolves the environment and writes Markdown atomically with `write --expect <observed-sha256-or-missing>`.

Deliver the plan, its entry path when persisted, and the material choices still open. A planning-only request stops here; planning inside authorized implementation returns to implementation. A plan by itself authorizes no agents, worktrees, commits or handoffs.
