---
name: orchestrate
description: Coordinate authorized agent work through native host tools; use managed execution only for a required native capability gap or an explicit runtime request.
---

# Orchestrate

Use orchestration to improve the accepted result enough to justify context and coordination cost. A full tree or workflow requires the user's request. Autonomous delegation is limited to economical reconnaissance or bounded assistance with a clear benefit. Respect explicit model and reasoning-effort choices; do not silently substitute or escalate them.

Before choosing a model for a delegated task, read [model selection](references/models.md). The delegating agent chooses the provider, model, and effort according to the assignment. Scout, worker, and coordinator describe responsibilities, without a preferred provider or fixed model mapping. The tools execute and record the choice; they do not make it.

## Choose the execution mechanism

Inspect the native agent tools and supported selection controls in the current session. Use them whenever they can honor the assignment's required model, effort, context, permissions, and lifecycle. Native execution is required in that case. Model differences within the same host do not constitute cross-host work: for example, a Claude Code parent delegates compatible Opus or Sonnet assignments through its native agent tools even when the parent uses another model.

Use Harness-managed execution only when a required capability is unavailable natively, such as access to an unsupported provider, or when the user explicitly requests the managed runtime. Before a managed launch, state the concrete missing capability and the evidence for that limitation, or identify the explicit runtime request. A request for subagents, roles, a graph, or a Harness work record does not select the runtime. Preference for Harness tracking or the availability of workflow templates is not a capability gap. A host name alone does not establish session capabilities; denied permission must not be bypassed through external execution.

## Scope ownership

Make the owner, outcome, boundaries, acceptance responsibility, and limits clear in each assignment. The primary agent owns work until a separate owner is assigned. An assigned owner conducts execution through completion or explicit reassignment: it plans, coordinates authorized participants, makes local decisions, follows up on results, and resolves corrections within its mandate. Apply this policy to individual tasks and any graph shape.

Ancestors receive progress and results, supply context, and coordinate their own boundaries. Route requests and corrections through the assigned owner. Do not direct its participants, implement its corrections, or require routine local decisions to return upward. Respect separately assigned review and integration authority: assess the agreed deliverable and return defects to its owner without taking over execution.

Resolve issues locally while the assignment permits it. Escalate a concrete blocker only when it requires scope, authority, context, resources, or capabilities the owner lacks. State the specific decision or assistance needed and retain responsibility for the remaining work. Questions spanning scopes go to the owner of the shared boundary. Reports, requests for help, failed attempts, and waiting do not transfer ownership or turn remaining work into instructions for an ancestor to execute.

Reassignment requires explicit authorization and a clear handoff to the affected agents; being an ancestor alone does not grant that authority. Preserve context and reconcile active work before a replacement proceeds. The user's stop and execution limits still apply. Ownership does not grant new permissions or bypass configured acceptance roles.

## Execution and continuity

For native agents, use the host's lifecycle and identifiers. Keep durable context, decisions, and results in Harness records when useful. Native agents are not Harness-managed participants: the runtime does not track or enforce their individual limits, messages, or cancellation. Each delegating agent must account for completion and stopping of the native agents it starts within the agreed limits. These lifecycle obligations do not authorize bypassing a designated scope owner.

When already participating in a managed run, preserve its configured graph, identity, decisions, and shared limits. A native helper remains part of the parent's assignment; collect its result and finish or stop it before returning. Use native help only when these constraints can be honored. Do not replace configured participants or leave native work running after the managed assignment ends.

Start with the task's coherent boundaries and available context. A module graph has a coordinator and configured workers. Assign each participant the context it needs, interfaces it owns, acceptance responsibility, and limits. Preserve the user's conversation language in the brief when the English work records would otherwise hide it. A child requests context outside its assignment from the parent. Parallelism alone is not token efficiency.

Use [develop](references/develop.md) or [review](references/review.md) for the requested workflow. Apply their responsibilities through native tools when native execution meets the assignment.

## Harness-managed execution

Read [managed execution](references/managed-execution.md) only after establishing the capability gap or explicit runtime request above, or when continuing an existing managed assignment. Keep this operational path separate from native delegation; Harness context and memory remain available with either mechanism.
