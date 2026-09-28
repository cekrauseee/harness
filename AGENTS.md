# Harness contributor guidance

## Scope

Harness provides file-native project context and focused engineering workflows. It is not an application, daemon, database, deployment platform or agent scheduler. Skills describe responsibilities; the helper handles only concrete filesystem guarantees.

## Language and scope

- Write repository documentation, commit messages, branches and pull requests in concise English.
- Keep one canonical source and link to it. Code and developer documentation must make sense without the internal execution plan.
- Include mechanisms for current requirements. Keep operational instructions independent of model names; use temporary team configuration for actual choices.
- Preserve unrelated work. Implementation does not authorize additional publication or installation actions beyond the user's request.

## Engineering

- Keep each published skill self-contained under `skills/<skill-name>/`.
- Use Python standard library only for bundled scripts.
- Make helper mutations atomic and idempotent; detect concurrent changes instead of overwriting them.
- Keep storage explicit and current-only. Do not add compatibility layers or automatic migration.
- Edit `src/harness.py` and `docs/file-context.md`; their copies in skills are generated.
- Keep one external environment per project, shared by its Git worktrees. New worktrees belong inside that environment.
- Do not add lifecycle hooks, automatic context injection, agent claims or mandatory work records.
- Never store secrets, chat transcripts or chain-of-thought in context files, or add environment state to a target repository.
- Use Conventional Commits and semantic branches such as `feat/access-control`. PRs describe the macro behavior in normal prose.

## Verification

Follow [development verification](docs/development.md), proportionate to the changed surface. Tests belong in `tests/`, outside installed skills, and establish mechanical or packaging guarantees. Do not test exact skill wording or encode semantic judgments as assertions. Independent evaluation is used only when authorized or required.
