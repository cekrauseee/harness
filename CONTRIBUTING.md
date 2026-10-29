# Contributing

Use Python 3.11+ on macOS or Linux. The checkout runs directly:

```sh
./bin/harness --help
./bin/harness doctor
python3 -m unittest discover -s tests -v
```

Select a maintained interpreter with `HARNESS_PYTHON` for the launcher when needed. Run the tests with that interpreter as well. No package dependencies or provider credentials are required for the deterministic test suite.

Tests use temporary data roots and fake provider executables. They exercise observable CLI flows and critical concurrency, authority, cancellation, budget, and recovery contracts. They do not call real models. Keep real provider smoke checks minimal and explicitly separate from this suite.

Keep source modules focused on their contracts. Human context remains Markdown; operational state remains SQLite. Preserve unknown user configuration fields and detect concurrent record updates. Add tests for meaningful behavior or critical invariants, not for implementation wording.

Product documentation belongs in `docs/`; process guidance belongs in `skills/`. Update only the affected guides and references. Internal plans and execution notes belong in a Harness environment outside this repository. Use Conventional Commit titles and the verified contributor identity; do not add automatic coauthor or generated-by attribution.

Before changing plugin packaging, validate both manifests against their supported host and verify the marketplace installation from an isolated configuration. Provider adapters must preserve native permissions and clearly report unsupported capabilities.
