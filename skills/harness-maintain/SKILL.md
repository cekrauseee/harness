---
name: harness-maintain
description: Diagnose Harness integrity, consolidate project knowledge, and guide explicitly authorized operational cleanup. Use for damaged state, stale or duplicate knowledge, or a concrete cleanup request.
---

# Harness Maintain

Inspect the specific problem before choosing a repair. Commands are relative to this installed skill directory.

```bash
python3 scripts/harness.py maintain --project /path/to/project
```

The report identifies structural problems, uncertain participation and knowledge needing review. Cards and journal views are derived from the canonical snapshot, so no separately authoritative index needs repair. Repeating a diagnostic does not rewrite timestamps or create work.

For cognitive consolidation, search and hydrate the relevant records, verify their sources, and select the smallest current account of the project. Use `memory.update` to correct a canonical record, improve its sources or aliases, or mark it stale, superseded or retracted. The update replaces that record; it does not append a copy of the prior payload. Create a new record only when the knowledge is meaningfully distinct. Do not preserve duplicate text solely because it is old.

Silence is not completion. Do not release active claims or erase pending work because a record is old. Reconcile ownership with evidence before allowing another writer into the same resources.

Operational cleanup is separate from the read-only `maintain` operation; Harness has no built-in reset. Perform cleanup only when the user explicitly authorizes the exact project and records, after participating writers have stopped. A user-scoped one-off administrative helper may hold the shared runtime lock and replace the snapshot atomically while preserving project identity and every collection outside the authorized scope. Do not treat cleanup as schema conversion or create an automatic backup. Validate the resulting snapshot before reporting success.

Use `guide` to inspect supported operation inputs. An unsupported schema or damaged file is an error to investigate; it is never treated as an empty project. Report what was checked, what changed and which semantic questions remain unresolved. Maintenance does not run in the background.
