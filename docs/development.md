# Development

Use Python 3.10+ on macOS or Linux. Bundled runtime and helpers use only the standard library. Node/npm are required only for the skills CLI distribution test.

## Source and distribution

`src/harness_runtime/` is the canonical runtime. The five directories in `skills/` contain task-specific instructions plus generated runtime copies. This duplication is a distribution artifact: skills CLI can install one directory without the repository root. Each copy includes its own launcher, implementation and required references. `scripts/build_dist.py --check` detects drift and unexpected scripts. State schemas reject incompatible clients instead of accepting partial updates blindly.

```bash
python3 scripts/build_dist.py
python3 scripts/build_dist.py --check
python3 -m unittest discover -s tests -v
```

The test suite covers state operations, concurrency, crashes/retries, host instruction changes and portable copied skills using temporary directories. It must not mutate the developer's Harness state or actual host installation. No server or browser is required.

Run the actual CLI package test separately:

```bash
python3 scripts/verify_install.py --workflows ../workflows
```

It disables telemetry and isolates installation configuration, copies source packages to disposable paths, tests selective/default/copy installations and executes their helpers after removing those package sources. It reports tool versions and timings. The sibling Workflows checkout is needed only for this cross-product verification, never by installed Harness.

Validate every skill with the installed Skill Creator validator and each plugin manifest with Plugin Creator's validator. Example paths in a standard Codex setup:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/harness-init
python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
DISABLE_TELEMETRY=1 npx skills add . --list
```

Repeat skill validation for all five directories. Validator dependencies belong to the development tools, not the distributed runtime. Publishing remains a separate authorized action.

## Repository responsibilities

- `core.py`: canonical state, identity, claims, checkpoints, knowledge and derived reports.
- `integration.py`: explicit managed host instruction block.
- `cli.py`: JSON input/output, operation guide and dispatch.
- `tests/`: executable behavior checks.

`DEFAULTS_VERSION` is 8. This prevents clients using the previous retention policy from writing current snapshots. Hooks are not part of the distribution. Tests and verification must use disposable state unless a user explicitly authorizes a concrete administrative change.
