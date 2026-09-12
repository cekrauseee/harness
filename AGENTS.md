# Continuity contributor guidance

## Scope

Continuity is a file-native project continuity and coordination layer for agents. It is not an application, daemon, database, deployment tool, or infrastructure manager.

## Language

- Write all repository-facing documentation, commit messages, branch names, and pull request content in English.
- Use simple, objective, coherent, and concise language.
- Keep one canonical source of truth and link to it instead of duplicating it.
- Include only guidance and mechanisms that serve a current requirement. Keep operational guidance independent of model names. Reuse context and verification, and expand them only for a relevant gap.

## Engineering conventions

- Use English Conventional Commits for repository contributions. Execution conventions belong to Workflows, not the Continuity runtime.
- Keep every published skill self-contained under `skills/<skill-name>/`.
- Use Python standard library only for bundled scripts.
- Make filesystem mutations atomic and idempotent.
- Keep the stored format explicit and current-only; do not add compatibility layers.
- Edit `src/continuity.py`; copies in skill script directories are generated.
- Do not add default lifecycle hooks or automatic prompt-context injection.
- Never store secrets, raw chat transcripts, or chain-of-thought in Continuity state.
- Never add Continuity state to a target repository.

## Verification

- Follow [development verification](docs/development.md), keeping checks proportional to the changed surface.
- Keep tests in `tests/` and outside installed skills. Test mechanical guarantees and packaging; do not encode semantic judgments or exact skill wording as assertions.
