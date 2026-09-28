# Host integration

Change host instructions only within the user's request. Preserve existing authority, unrelated sections, tool restrictions and explicit choices. Installing skills does not authorize rewriting a global AGENTS.md or CLAUDE.md.

A host entry should carry the few behaviors needed even without a loaded skill:

- Code and developer documentation must make sense without the agents' execution plan. Keep internal assignments, attempts and handoffs in the project's external environment.
- Use existing context first; locate the project environment or load a process skill only when it serves the task. A small solo change requires no work record.
- Execute directly unless delegation is requested or an authorized team is already active. Respect the user's model, effort and cost choices.
- Complete authorized work and sufficient verification. Reuse valid results; do not add approval, audit or testing loops without a concrete reason.
- Feature implementation does not itself authorize commit, push, PR, merge, release or deployment. Existing authorization persists for its scope.

The environment README contains its map and project-specific guidance. Skills define process responsibilities and outputs. Avoid copying entire skill procedures into the host entry or making every task read a chain of files. Do not add lifecycle hooks, automatic memory injection, prompt transcripts or a mandatory invocation list.

Use the host's real capabilities for agents, IDs, worktree operations and permissions. A worktree tool must be able to honor `<environment>/worktrees/<name>` before creation; a tool preference does not change the required destination. Do not invent parameters or silently substitute models. Store concrete team settings only in the work's temporary `team.md`.

When replacing earlier tooling, identify active consumers before removing discovery entries or helper paths. Preserve legacy knowledge and continuations separately; Harness does not read or migrate old state implicitly. Validate the newly installed inventory in a fresh host session before declaring the replacement effective.
