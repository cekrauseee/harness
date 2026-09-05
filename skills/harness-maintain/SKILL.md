---
name: harness-maintain
description: Diagnose damaged, stale or legacy Harness state and perform explicit migration or installation cleanup with previews and recovery. Use for integrity failures, outdated state or a concrete maintenance need.
---

# Harness Maintain

Inspect the specific problem before choosing a repair. Commands are relative to this installed skill directory.

```bash
python3 scripts/harness.py maintain --project /path/to/project
```

The report identifies structural problems, uncertain participation and knowledge needing review. Cards and journal views are derived from the canonical snapshot, so no separately authoritative index needs repair. Repeating a diagnostic does not rewrite timestamps or create work.

Silence is not completion. Do not release claims, approve tasks or erase pending actions because a record is old. Reconcile ownership with evidence before allowing another writer into the same resources. Mechanical cleanup must not make semantic decisions.

For legacy state, old skill installations or hook configuration, read [migration.md](references/migration.md). Begin with `migrate.preview` or `legacy.scan`. Applying a migration requires its current fingerprint, stopped legacy writers and authorization for the selected state. A verified backup is the default; use the documented no-backup option only when the user explicitly declines a backup. Development tests should use temporary homes. Do not test a migration against the user's real state.

Use `guide` to inspect operation inputs. An invalid schema, damaged file or changed source is an error to investigate; it is never treated as an empty project. Future schema versions must be opened with a compatible runtime. Report what was checked, what changed and which semantic questions remain unresolved. Maintenance does not run in the background.
