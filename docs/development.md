# Development

Edit `src/continuity.py`; copies under skills are generated. Search and review the canonical source instead of repeating the same investigation across copies. Keep bundled code in the Python standard library and tests outside skills.

| Changed surface | Verification |
| --- | --- |
| Prose or links | Review the affected meaning, scope and references |
| Skill or manifest metadata | Validate affected files with available host validators and check inventory alignment |
| Skill behavior | Assess realistic requests for the changed behavior and preserve authorization boundaries |
| Helper behavior or test logic | Run tests for the affected contract; use the full suite for shared identity, ownership or persistence changes |
| Helper distribution | Generate copies and check equality |
| Package layout, discovery or installation | Check the affected installation boundary in disposable destinations |

This table defines the repository-specific check scope. Editorial changes do not require runtime or installation tests. Host validators are optional tools, not repository dependencies. When unavailable, inspect the affected metadata and state the verification limit. Behavioral evaluation must assess actual outcomes, not match wording or impose a test framework for prose. Independent agent evaluations need authorization for delegation and any associated costs.

For changes to shared helper mechanisms:

```bash
python3 -B -m unittest discover -s tests -v
python3 -B scripts/build_dist.py
python3 -B scripts/build_dist.py --check
```

The suite uses disposable projects to check identity, concurrent ownership, safe persistence, scoped retrieval and completion. Generation only updates its helper copies and preserves other skill resources. Byte equality and an installation smoke check cover the copies; helper tests run against the canonical source, not each copy.

For distribution changes:

```bash
python3 -B tests/verify_install.py
```

This separate check uses a pinned skills CLI and isolated homes to test each skill in copy and symlink modes for Codex and Claude Code. It removes the source, checks the selected inventory and payload, and runs the installed helper once. `--cli /path/to/bin/cli.mjs` uses an existing CLI. Ordinary local tests need neither Node nor network access.

Before requested publication, validate the complete skill inventory and aligned manifests, inspect the final diff and verify discovery with `npx skills add . --list`. Installation checks are needed when distribution behavior changed. Keep repository URLs and MIT authorship intact. Commit, push, release, publication and user installation changes remain within their respective authorization; do not request it again when already granted.
