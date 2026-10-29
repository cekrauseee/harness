# Writing guidance

Skills describe the user's process in terms a capable agent can apply across models. Include the desired outcome, relevant context, real boundaries, and evidence that would establish completion. Explain a procedure in detail when its order or domain knowledge matters; leave ordinary judgment to the agent.

Use short, discriminating descriptions. Load the skill body only when it applies and substantial references only for the active mode. Preserve user scope and established authorization. Avoid repeated manuals, generic encouragement, mandatory surveys before trivial edits, and rigid recipes that substitute for understanding. These principles align with OpenAI's [skills and prompts guidance](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra).

Make instructions clear and supply the context that changes a decision. Examples should clarify a real ambiguity, not become universal requirements. Conditional guidance and suitable task boundaries are more portable than a long list of compensations for one model. See Anthropic's [prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices).

Model-specific advice belongs in evaluated profile choices or narrow integration guidance. In particular, effort labels and defaults do not represent equal work across models. Test the cost/quality tradeoff on representative tasks rather than assuming the highest effort is best or copying a previous model's setting. Both the [Fable guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1) and [Opus guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5) motivate that calibration.

Keep completion criteria and useful state explicit so an agent can continue the requested work without repeating permission questions or reconstructing everything after compaction. Preserve uncertainty and unresolved decisions. Evaluate instructions through representative behavior, not word counts or assertions that a particular phrase exists.
