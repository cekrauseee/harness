# Audit contract

Audit is read-only by default. A repair must be deterministic, reconstruct a derived file from authoritative records, and require an explicit flag.

`memory/catalog.jsonl` is derived from active records below `memory/topics/`, so catalog rebuilding is safe. Candidates, topic records, archived items, sessions, manifests, project documentation, locks, and workspaces are authoritative or user-owned state and must not be deleted or rewritten by audit.

Stale session and lock findings are recommendations, not cleanup authorization.
