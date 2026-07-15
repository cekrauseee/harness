# Memory lifecycle

```text
observation -> candidate -> classification -> topic or archive
```

Durable topic memory is project-scoped, current operational knowledge that is useful across tasks but does not belong in versioned documentation. Examples include an unresolved compatibility constraint or an investigation result awaiting a product decision.

Use `documentation` for stable architecture, setup, contract, module, or workflow knowledge. Use `rule` for mandatory agent behavior that belongs in project instructions. These classifications produce routing actions; this skill does not edit the repository.

Superseded records remain inspectable in `memory/archive/` and disappear from recall. `memory/catalog.jsonl` is a deterministic, rebuildable projection of active topic records.
