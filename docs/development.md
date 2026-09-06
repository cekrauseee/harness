# Development

`src/harness.py` is the one canonical runtime helper. It uses Python 3.10+ standard library and POSIX file locking. Skill script copies are generated; edit the source, then run:

```bash
python3 scripts/build_dist.py
python3 scripts/build_dist.py --check
python3 -m unittest discover -s tests -v
```

The local suite in `tests/test_kernel.py` checks the helper's mechanical guarantees in disposable directories. Related input variants use named subtests; independent concurrency and filesystem risks remain separate. It must not touch actual user state. `HARNESS_TEST_HELPER=/absolute/copied/scripts/harness.py` runs the same suite against an independently copied helper.

It covers project identity, resource contention, current handoff persistence, observed-content writes, failures before and after replacement, and filesystem boundaries. These tests do not evaluate what an agent should remember or how it interprets a skill. Instruction changes need review of scope, clarity and realistic usage; automated checks cannot establish that semantic behavior.

Keep validation proportional to the change. Run the local suite for helper or test changes and check generated copies when the helper changes. For skill edits, use the host's skill validators and review the actual instructions; for manifest edits, use its plugin validator. Before publication, validate all skills and the manifest, run `python3 scripts/build_dist.py --check`, and inspect discovery with `npx skills add . --list`.

Verify actual skills CLI distribution separately when installation or packaging changes, or before publishing a changed distribution:

```bash
python3 tests/verify_install.py
# Include the independent sibling package when that distribution is in scope:
python3 tests/verify_install.py --workflows ../workflows
```

This opt-in check uses an isolated home for each published skill and installation mode. It selects one skill from the whole package, removes the source, checks the exact installed inventory and payload for Codex and Claude Code, and initializes a temporary project with each installed Harness helper. It verifies packaging without repeating the helper's ownership and document tests or testing the skills CLI's update/removal lifecycle. Workflows requires no runtime execution. The sibling checkout is only a development verification input, never an installed dependency.

The integration check is outside `unittest` discovery: ordinary local tests require neither Node nor network access. Installation uses Node and a pinned skills CLI; `--cli /path/to/bin/cli.mjs` selects an existing CLI. Tests stay in this repository and are not bundled into installed skills. No development server or browser is needed.

There is no migration service or automatic archive. Deliberate changes to user knowledge or stored format are agent-led maintenance under explicit scope. Keep private state outside repositories and do not add implementation solely to preserve old contracts.
