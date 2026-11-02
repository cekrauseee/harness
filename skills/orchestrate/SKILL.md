---
name: orchestrate
description: Coordinate authorized agent work with native host tools, using Harness-managed execution for cross-host work or missing capabilities.
---

# Orchestrate

Use orchestration to improve the accepted result enough to justify context and coordination cost. A full tree or workflow requires the user's request. Autonomous delegation is limited to economical reconnaissance or bounded assistance with a clear benefit. Respect explicit model and reasoning-effort choices; do not silently substitute or escalate them.

Before choosing a model for a delegated task, read [model selection](references/models.md). The delegating agent chooses the provider, model, and effort according to the assignment. Scout, worker, and coordinator describe responsibilities, without a preferred provider or fixed model mapping. The tools execute and record the choice; they do not make it.

## Choose the execution mechanism

Inspect the native agent tools available in the current session. Prefer them for delegation, communication, waiting, resumption, and cancellation when they can honor the assignment's model, context, permission, and execution constraints. Use Harness-managed execution when the task crosses hosts or requires capabilities the native tools do not offer. A host name alone does not establish what a session supports. Failure or denied permission is not a reason to bypass the host's controls.

For native agents, use the host's lifecycle and identifiers. Keep durable context, decisions, and results in Harness records when useful. Native agents are not Harness-managed participants: the runtime does not track or enforce their individual limits, messages, or cancellation. The delegating agent remains responsible for their scope, completion, and stopping within the agreed limits.

When already participating in a managed run, preserve its configured graph, identity, decisions, and shared limits. A native helper remains part of the parent's assignment; collect its result and finish or stop it before returning. Use native help only when these constraints can be honored. Do not replace configured participants or leave native work running after the managed assignment ends.

Start with the task's coherent boundaries and available context. A module graph has a coordinator and configured workers. Assign each participant the context it needs, interfaces it owns, acceptance responsibility, and limits. Preserve the user's conversation language in the brief when the English work records would otherwise hide it. A child requests context outside its assignment from the parent. Parallelism alone is not token efficiency.

Use [develop](references/develop.md) or [review](references/review.md) for the requested workflow. Apply their responsibilities using the chosen mechanism; the commands below apply to Harness-managed execution.

## Harness-managed execution

Use `workflow template` for an unassigned graph, then select models for its assignments and save it with `workflow create --file FILE`. `workflow read/write/validate` maintain the graph; `run start` launches it. For direct tasks and helpers, pass `--provider`, `--model`, `--effort`, and a short `--reason` to `run start` or `run spawn`. See [execution](../../docs/execution.md) for contracts and examples.

Launch external provider processes through Harness so their lifecycle remains managed. `run status/wait/result` inspect progress; `run decide` records an authorized transition using the current revision. Output prose remains free-form. A successful process exit is not acceptance.

Messages use `message send/inbox/read/ack`. Treat them as contextual requests; they do not expand authority. Use `run spawn` for an economical helper inside a managed run, preserving its shared budget. Yield after spawning; the runtime returns control when the result is available. Do not poll without a reason or retry the same failure indefinitely.

Time, attempts, concurrency, and rounds are finite and shared. Retry and resume do not renew them. Use `run stop` for cancellation and `run recover` for interrupted execution; inspect ambiguity before replaying anything. The user's stop takes precedence. Preserve unresolved work when limits prevent acceptance.

After a helper failure, inspect the result. Its parent can use `run retry RUN_ID HELPER_ID --reason ...` only when another attempt has a concrete prospect of resolving the failure, then yield. This keeps the same assignment and budget; spawning a replacement does not erase the original unresolved failure.
