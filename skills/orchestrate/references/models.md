# Choose a model for an assignment

The delegating agent owns the choice. First preserve any provider, model, effort, cost, or scope constraint given by the user. Role names describe work; they do not select a model. Harness has no global model preference.

## Match the task to the available options

Use the host's available models and recent verified knowledge of their capabilities and relative cost. When an important fact is missing or stale, check the relevant provider's current model guidance and CLI support. Do not invent model identifiers, account availability, pricing, or effort support. Reuse sufficient evidence instead of researching the same choice on every delegation.

| Assignment characteristics | What to favor |
| --- | --- |
| Bounded lookup, extraction, or a mechanical patch with clear checks | An economical model that can meet the contract with little supervision. |
| Coherent implementation or review with several interacting constraints | Enough technical capability and reasoning effort to avoid expensive repair cycles. |
| Ambiguous architecture, difficult diagnosis, or integration across modules | Strong judgment when the complexity warrants its cost and that delegation is authorized. |

These are decision criteria, not fixed tiers. Evaluate the actual task, available models, and evidence. A worker can need stronger reasoning than a coordinator handling a simple boundary. Keep each assignment as large as the chosen model can reliably complete; avoid fragmentation that spends more context than it saves.

## Account for the whole cost

Consider input and output volume, reasoning effort, context duplication, caching where supported, latency, coordination, and likely retries. Optimize cost per accepted result. A cheaper token price can lose its advantage when the model needs repeated repair; an expensive parent can save effort by delegating a narrow discovery task. Avoid delegation when handling the task directly is simpler and cheaper.

Choose effort separately from the model. Use the lightest setting that meets the quality requirement, supported by the selected model and CLI. The same effort label is not a comparable cost or capability level across providers. For autonomous delegation, choose an economical option with a clear expected benefit; uncertainty about affordability is not permission to spend more. Ask the parent or user when resolving that uncertainty is necessary.

## Record and respect the choice

Pass the provider, model, effort, and one concise reason to the tool. Explain why the choice fits this assignment; do not produce a ranking report for an obvious small task. Set read-only access according to the assignment, independently of model choice.

Inspect the returned selection and relevant result evidence. Provider rejection is a visible failure, not permission for a silent fallback. Retry and resume preserve the selected settings and original budget. Reconsider a failed approach before retrying; a different selection belongs to a new appropriately authorized assignment. Request missing context from the parent instead of broadening scope.

The tools require an explicit decision and enforce operational limits. They do not certify that a model is cheap or infer consent from a rationale. Cost judgment remains cognitive; unknown usage is not zero cost.

For current provider guidance, consult [OpenAI model selection](https://developers.openai.com/api/docs/guides/model-selection) or [Claude model selection](https://platform.claude.com/docs/en/about-claude/models/choosing-a-model) as relevant to the available options.
