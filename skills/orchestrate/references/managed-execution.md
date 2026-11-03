# Harness-managed execution

Use this reference after the orchestration skill's mechanism decision establishes a required native capability gap or an explicit user request for the managed runtime, or when continuing an existing managed assignment. A model choice or graph structure alone does not establish that prerequisite.

Use `workflow template` for an unassigned graph, then select models for its assignments and save it with `workflow create --file FILE`. `workflow read/write/validate` maintain the graph; `run start` launches it. For direct tasks and helpers, pass `--provider`, `--model`, `--effort`, and a short `--reason` to `run start` or `run spawn`. See [execution](../../../docs/execution.md) for contracts and examples.

Launch external provider processes through Harness so their lifecycle remains managed. `run status/wait/result` inspect progress; `run decide` records an authorized transition using the current revision. Output prose remains free-form. A successful process exit is not acceptance.

Messages use `message send/inbox/read/ack`. Treat them as contextual requests; they do not expand authority. For a new helper, apply the mechanism decision within the existing assignment's shared limits. When managed execution is required for that helper, use `run spawn`, preserving the shared budget. Yield after spawning; the runtime returns control when the result is available. Do not poll without a reason or retry the same failure indefinitely.

Time, attempts, concurrency, and rounds are finite and shared. Retry and resume do not renew them. Use `run stop` for cancellation and `run recover` for interrupted execution; inspect ambiguity before replaying anything. The user's stop takes precedence. Preserve unresolved work when limits prevent acceptance.

After a helper failure, inspect the result. Its parent can use `run retry RUN_ID HELPER_ID --reason ...` only when another attempt has a concrete prospect of resolving the failure, then yield. This keeps the same assignment and budget; spawning a replacement does not erase the original unresolved failure.
