# Memory lifecycle

Harness memory is explicit, file-native, scoped, and auditable. It replaces project continuity, not personal host preferences or the host execution model.

## Scopes

- Global memory contains explicitly accepted preferences that apply across projects.
- Project memory contains operational facts, provisional decisions, and expensive-to-rediscover context.
- Session state contains an episodic continuation handoff for material work.
- Stable developer knowledge belongs in versioned project documentation.

## Lifecycle

```text
candidate -> classify -> deduplicate -> activate, promote, or discard
          -> search card -> hydrate selected record -> verify
          -> stale, supersede, dormant, closed, or archive
```

Every searchable record has a semantic title, short summary, conditional read rule, tags, status, update time, and optional artifact references. The generated catalog indexes those compact cards without full content.

Search returns a small ranked card set and no content. The agent hydrates only a selected ID under an explicit budget. Weak matches return no context. This keeps large records discoverable without injecting them and prevents unrelated sessions from entering the prompt.

Durable items include provenance, a freshness signal, and a review date. Explicitly installed adapters may update maintenance metadata but never inject context or promote a candidate. Recall excludes workspace files and stale or inactive records by default.

## Sessions

Do not create a session for every conversation. Start one lazily when material work may require a handoff. Keep the current session active, mark interrupted but relevant work dormant, and close completed work. Search may still find dormant or closed sessions at lower priority when their semantic card strongly matches.

## Content boundaries

Never store secrets, credentials, raw chat transcripts, chain-of-thought, routine command output, obvious source facts, or build artifacts. Every durable item must provide provenance, a conditional read rule, and a freshness signal.

## Workspace

The workspace is an isolated, temporary area for agent-owned intermediates. It is excluded from memory catalogs and recall. Session-start hooks remove files older than seven days by default; `workspace/policy.local.json` can override the age. Final documentation artifacts are promoted to `docs/artifacts/`.
