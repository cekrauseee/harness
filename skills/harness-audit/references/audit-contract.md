# Audit and migration contract

Audit is read-only by default. A repair must be deterministic, reconstruct a derived file from authoritative records, and require an explicit flag.

`memory/catalog.jsonl` is derived from active records below `memory/topics/`, so catalog rebuilding is safe. Candidates, topic records, archived items, sessions, manifests, project documentation, locks, and workspaces are authoritative or user-owned state and must not be deleted or rewritten by audit.

Stale session and lock findings are recommendations, not cleanup authorization.

## Explicit schema migration

`--migrate` is a separate, user-authorized operation. `--dry-run` reports the exact files and moves without changing state. Before the first selected project is changed, migration copies every selected project that needs work to one timestamped directory below `HARNESS_HOME/backups/`.

Migration may:

- upgrade manifests to schema v2 and derive path or Git bindings from legacy arrays;
- add deterministic semantic fields to sessions and memory;
- move empty or stale active sessions to `sessions/dormant/`;
- preserve a live session ID and deterministically rekey the closed copy when they conflict, retaining the old value as `legacy_id`;
- convert non-UUID record IDs deterministically and retain the original as `legacy_id`;
- normalize scalar tags and artifact references into one-item lists without dropping them;
- rebuild the derived session-and-memory catalog.

Migration must preserve original content, archived records, closed sessions, project documents, references, workspaces, and policies. A fallback title or summary may only be a short extract from existing fields or an explicit unlabeled marker. It must never invent project facts. Repeating a completed migration must produce zero changes and no new backup.
