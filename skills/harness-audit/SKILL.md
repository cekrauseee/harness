---
name: harness-audit
description: Audit and safely migrate Harness identity, bindings, semantic records, catalogs, sessions, locks, budgets, and global storage. Use when project continuity is stale, noisy, missing, interrupted, legacy, or due for maintenance.
---

# Harness Audit

Inspect the global Harness without changing project code or documentation.

## Run an audit

Audit the current project:

```bash
python3 scripts/audit.py --project <project-path> --json
```

Audit every global project:

```bash
python3 scripts/audit.py --all --json
```

Use `--project <project-path>` for the canonical project-native form; `--repo` remains a compatibility alias. The audit reports:

- malformed or mismatched project identities and bindings;
- missing required global container paths;
- invalid memory, candidate, archive, or session JSON;
- catalog drift from active topic memory;
- empty, stale, or excessive active sessions and locks;
- semantic records missing useful titles, summaries, read rules, or tags;
- oversized or unrecallable memory and recall-card accounting overhead;
- registered project paths that no longer exist;
- any Harness-owned `.harness` or `.project-harness` directory found at a registered project root.

Use `--repair-catalog` only to atomically rebuild the derived `catalog.jsonl`. It does not classify memory, close sessions, remove locks, or edit repositories.

## Migrate legacy state

Preview every planned change first:

```bash
python3 scripts/audit.py --all --migrate --dry-run --json
```

Apply the deterministic schema migration:

```bash
python3 scripts/audit.py --all --migrate --json
```

Migration creates one timestamped backup below `~/.harness/backups/` before changing any selected project. It adds project-native bindings and compact semantic fields, rebuilds the derived session-and-memory catalog, and moves empty or stale active sessions to `sessions/dormant/`. It preserves full memory content and every legacy session. If a live and closed session share an old ID, it preserves the live ID, deterministically rekeys the closed copy, and records `legacy_id`. Non-UUID legacy IDs are converted the same way so core recall can hydrate them by canonical ID.

Run migration only when the user authorized state changes. Prefer `--project <path>` or `--project-id <uuid>` for one project. A repeated migration with no pending changes creates no backup and changes nothing.

## Interpret severity

- `error`: integrity is broken; do not trust affected recall until repaired.
- `warning`: state may be stale or require human classification.
- `info`: maintenance counts or healthy observations.

The command exits nonzero only when errors exist. Read [references/audit-contract.md](references/audit-contract.md) before adding new repair behavior.
