# Development

`src/harness.py` is the one canonical runtime helper. It uses Python 3.10+ standard library and POSIX file locking. Skill script copies are generated; edit the source, then run:

```bash
python3 scripts/build_dist.py
python3 scripts/build_dist.py --check
python3 -m unittest discover -s tests -v
```

The unit suite checks identity, contention, current handoff persistence, observed-content writes and path boundaries in disposable directories. It must not touch actual user state. `HARNESS_TEST_HELPER=/absolute/copied/scripts/harness.py` runs the same suite against an independently copied helper.

Verify the actual skills CLI distribution separately:

```bash
python3 scripts/verify_install.py --workflows ../workflows
```

That script isolates child-process homes, checks copy/symlink installations and updates, removes the source package, and exercises installed capabilities. Workflows requires no runtime execution. The sibling checkout is only a development verification input, never an installed dependency.

Validate every skill and plugin manifest with the host's available validators, and run `npx skills add . --list` before publication. These tools belong to the host rather than either plugin. No development server or browser is needed for the filesystem guarantees.

There is no migration service or automatic archive. Deliberate changes to user knowledge or stored format are agent-led maintenance under explicit scope. Keep private state outside repositories and do not add implementation solely to preserve old contracts.
