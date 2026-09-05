# Harness contributor guidance

## Scope

Harness is a file-native project continuity and coordination layer for agents. It is not an application, daemon, database, deployment tool, or infrastructure manager.

## Language

- Write all repository-facing documentation, commit messages, branch names, and pull request content in English.
- Use simple, objective, coherent, and concise language.
- Keep one canonical source of truth and link to it instead of duplicating it.

## Engineering conventions

- Use English Conventional Commits for repository contributions. Execution conventions belong to Workflows, not the Harness runtime.
- Keep every published skill self-contained under `skills/<skill-name>/`.
- Use Python standard library only for bundled scripts.
- Make filesystem mutations atomic and idempotent.
- Bump `DEFAULTS_VERSION` when managed Harness defaults change.
- Do not add default lifecycle hooks or automatic prompt-context injection.
- Never store secrets, raw chat transcripts, or chain-of-thought in Harness state.
- Never add Harness state to a target repository.

## Verification

- Run `python3 -m unittest discover -s tests -v`.
- Validate every skill with the bundled skill validator.
- Validate `.codex-plugin/plugin.json` with the plugin validator.
- Run `npx skills add . --list` before publication.
