---
name: harness-remember
description: Capture, classify, consolidate, supersede, or archive project memory in the global Harness. Use when preserving an expensive-to-rediscover observation, reviewing automatic memory candidates, promoting a candidate into a durable topic, or routing stable knowledge to versioned documentation or agent rules.
---

# Harness Remember

Manage the memory lifecycle explicitly. Automatic hooks may create candidates, but only classification may create durable topic memory.

## Capture a candidate

```bash
python3 scripts/remember.py candidate \
  --repo <repository> \
  --topic authentication \
  --content "Mobile clients still use the legacy refresh endpoint." \
  --read-when "when work involves mobile authentication" \
  --review-after-days 90 \
  --source-session <session-id> \
  --json
```

Capture only information that would be costly to rediscover. Do not capture temporary attempts, copied documentation, secrets, or facts already canonical in the repository.

## Classify a candidate

Inspect candidates with `list --status candidate`, then choose exactly one destination:

```bash
python3 scripts/remember.py consolidate \
  --repo <repository> \
  --candidate-id <uuid> \
  --classification topic \
  --json
```

Classifications:

- `topic`: promote into segmented durable memory and rebuild the catalog;
- `documentation`: archive with an action for the documentation workflow;
- `rule`: archive with an action for the project's agent instructions;
- `archive`: retain as historical evidence without recall;
- `discard`: retain only a minimal tombstone explaining rejection.

Use `--supersedes <memory-id>` with `topic` when replacing an earlier memory. Exact duplicates are archived instead of creating another durable entry.

## Invariants

- Never promote automatically captured candidates without classification.
- Keep one fact or tightly related fact set per memory item.
- Give durable items a conditional read rule and a deliberate review interval.
- Use topic slugs based on stable project concepts, not task names.
- Route stable developer documentation to the repository; do not duplicate it in memory.
- Never write Harness state into the repository.

Read [references/memory-lifecycle.md](references/memory-lifecycle.md) before resolving ambiguous classifications.
