# Memory lifecycle

Harness memory is explicit, file-native, scoped, and auditable. It replaces project continuity, not personal host preferences or the host execution model.

## Scopes

- Global memory contains explicitly accepted preferences that apply across projects.
- Project memory contains operational facts, provisional decisions, and expensive-to-rediscover context.
- Session state contains the minimum continuation handoff.
- Stable developer knowledge belongs in versioned project documentation.

## Lifecycle

```text
candidate -> classify -> deduplicate -> activate, promote, or discard
          -> budgeted recall -> verify -> stale, supersede, or archive
```

Automatic adapters update timestamps and recall context, but never persist raw prompts, responses, or transcripts. Injected behavior rules direct agents to create concise checkpoints and candidates without asking the user. Durable items include a conditional read rule, verification timestamp, and review date. Hooks never promote a candidate to durable memory. Recall excludes workspace files, inactive memory, and items past their review date by default.

## Content boundaries

Never store secrets, credentials, raw chat transcripts, chain-of-thought, routine command output, obvious source facts, or build artifacts. Every durable item must provide provenance, a conditional read rule, and a freshness signal.

## Workspace

The workspace is an isolated, temporary area for agent-owned intermediates. It is excluded from memory catalogs and recall. Session-start hooks remove files older than seven days by default; `workspace/policy.local.json` can override the age. Final documentation artifacts are promoted to `docs/artifacts/`.
