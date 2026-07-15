---
name: harness-audit
description: Audit global Harness identity, manifests, segmented memory, catalogs, sessions, locks, and non-versioned storage boundaries. Use when Harness context appears stale or missing, after an interrupted write, during periodic maintenance, or before trusting a project handoff. Repairs only rebuild derived catalogs when explicitly requested.
---

# Harness Audit

Inspect the global Harness without changing project code or documentation.

## Run an audit

Audit the current project:

```bash
python3 scripts/audit.py --repo <repository> --json
```

Audit every global project:

```bash
python3 scripts/audit.py --all --json
```

The audit reports:

- malformed or mismatched project identities;
- missing required global container paths;
- invalid memory, candidate, archive, or session JSON;
- catalog drift from active topic memory;
- stale active sessions and locks;
- repository paths that no longer exist;
- any Harness-owned `.harness` or `.project-harness` directory found at a registered repository root.

Use `--repair-catalog` only to atomically rebuild the derived `catalog.jsonl`. It does not classify memory, close sessions, remove locks, or edit repositories.

## Interpret severity

- `error`: integrity is broken; do not trust affected recall until repaired.
- `warning`: state may be stale or require human classification.
- `info`: maintenance counts or healthy observations.

The command exits nonzero only when errors exist. Read [references/audit-contract.md](references/audit-contract.md) before adding new repair behavior.
