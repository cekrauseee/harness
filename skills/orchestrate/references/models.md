# Choose a model for an assignment

The delegating agent owns the choice. First preserve any provider, model, effort, cost, or scope constraint given by the user. Role names describe work; they do not select a model. Harness has no global model preference.

## Match the task to the available options

Use the models available through the chosen execution mechanism and recent verified knowledge of their capabilities and relative cost. When an important fact is missing or stale, check the relevant provider's current model guidance and the mechanism's supported controls. Do not invent model identifiers, account availability, pricing, or effort support. Reuse sufficient evidence instead of researching the same choice on every delegation.

| Assignment characteristics | What to favor |
| --- | --- |
| Bounded lookup, extraction, or a mechanical patch with clear checks | An economical model that can meet the contract with little supervision. |
| Coherent implementation or review with several interacting constraints | Enough technical capability and reasoning effort to avoid expensive repair cycles. |
| Ambiguous architecture, difficult diagnosis, or integration across modules | Strong judgment when the complexity warrants its cost and that delegation is authorized. |

These are decision criteria, not fixed tiers. Evaluate the actual task, available models, and evidence. A worker can need stronger reasoning than a coordinator handling a simple boundary. Keep each assignment as large as the chosen model can reliably complete; avoid fragmentation that spends more context than it saves.

## Account for the whole cost

Consider input and output volume, reasoning effort, context duplication, caching where supported, latency, coordination, and likely retries. Optimize cost per accepted result. A cheaper token price can lose its advantage when the model needs repeated repair; an expensive parent can save effort by delegating a narrow discovery task. Avoid delegation when handling the task directly is simpler and cheaper.

Choose effort separately from the model. Use the lightest setting that meets the quality requirement, supported by the selected model and execution mechanism. The same effort label is not a comparable cost or capability level across providers. For autonomous delegation, choose an economical option with a clear expected benefit; uncertainty about affordability is not permission to spend more. Ask the parent or user when resolving that uncertainty is necessary.

## Record and respect the choice

For native delegation, use the selection controls the host actually exposes. Check supported per-invocation overrides, native subagent configuration, and inheritance before declaring a required choice unavailable. Some tools inherit the current model or effort; account for that inheritance instead of inventing parameters or claiming an unavailable override. If the required choice is supported natively, use native execution. A different child model does not require a different runtime. When a required choice cannot be honored natively, apply the orchestration skill's managed-execution exception and state the concrete limitation before launch.

For Harness-managed execution, pass the provider, model, effort, and one concise reason to the tool. Explain why the choice fits this assignment; do not produce a ranking report for an obvious small task. Set read-only access according to the assignment, independently of model choice.

Inspect the returned selection and relevant result evidence. Provider rejection is a visible failure, not permission for a silent fallback. Retry and resume preserve the selected settings and original budget. Reconsider a failed approach before retrying; a different selection belongs to a new appropriately authorized assignment. Request missing context from the parent instead of broadening scope.

Harness execution tools require an explicit decision and enforce their operational limits for managed participants. Native controls belong to the host. Neither mechanism certifies that a model is cheap or infers consent from a rationale. Cost judgment remains cognitive; unknown usage is not zero cost.

Consult the selected provider's current model-selection documentation when the available evidence is insufficient.
