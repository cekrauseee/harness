# Harness contributor guidance

## Scope

Harness provides file-native project context and focused engineering workflows, and is becoming a local visualization product for agent work. It is not a daemon, database, deployment platform or agent scheduler. Skills describe responsibilities; bundled scripts provide filesystem guarantees, derive facts from Git and host output, and start or wait for one host run on an agent's explicit command (no queue, no autonomous dispatch, bounded retry only when requested).

Installed skills remain Python standard-library scripts plus static references. Application source, such as the map viewer, lives under `apps/` outside `skills/` and is never installed. The map skill's data is the deliverable; viewing it requires the local viewer app (Node and pnpm), and the data stays valid without it.

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
- Edit `src/*.py`, `schema/*.json` and the docs that `scripts/build_dist.py` lists; their copies in skills are generated.
- Application code under `apps/` follows its own README (stack, structure, checks); Python tests never require Node.
- Keep one external environment per project, shared by its Git worktrees. Worktrees Harness creates default to that environment; host-managed worktrees are accepted where they are.
- Do not add lifecycle hooks, automatic context injection or agent claims. Solo work needs no records. An orchestration records events and run deliveries under its fronts as [execution records](docs/records.md) describes; raw host output is evidence, not context.
- Never store secrets, chat transcripts or chain-of-thought in context files, or add environment state to a target repository.
- Use Conventional Commits and semantic branches such as `feat/access-control`. PRs describe the macro behavior in normal prose.

## Verification

Follow [development verification](docs/development.md), proportionate to the changed surface. Tests belong in `tests/`, outside installed skills, and establish mechanical or packaging guarantees. Do not test exact skill wording or encode semantic judgments as assertions. Independent evaluation is used only when authorized or required.
