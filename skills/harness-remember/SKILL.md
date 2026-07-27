---
name: harness-remember
description: Capture and classify concise durable project memory. Use when a verified fact is expensive to rediscover, a candidate needs disposition, or stable knowledge should move to documentation or rules.
---

# Harness Remember

Manage the memory lifecycle explicitly. Only classification may create durable topic memory.

## Capture a candidate

```bash
python3 scripts/remember.py \
  --project <project-path> \
  --json \
  candidate \
  --topic authentication \
  --title "Legacy mobile refresh endpoint" \
  --summary "Mobile clients still use the legacy refresh endpoint." \
  --content "Mobile clients still use the legacy refresh endpoint." \
  --read-when "when work involves mobile authentication" \
  --tag mobile \
  --tag authentication \
  --tag compatibility \
  --review-after-days 90 \
  --source-session <session-id>
```

Capture only information that would be costly to rediscover. Give it a semantic title, compact summary, conditional read rule, focused tags, and optional artifact references. Keep one fact or tightly related fact set per item. Large source material may remain in full content because recall indexes its compact card and hydrates content only on selection.

## Classify a candidate

Inspect candidates with `list --status candidate`, then choose exactly one destination:

```bash
python3 scripts/remember.py \
  --project <project-path> \
  --json \
  consolidate \
  --candidate-id <uuid> \
  --classification topic
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
- Keep titles and summaries useful without exposing the full content.
- Use topic slugs based on stable project concepts, not task names.
- Route stable developer documentation to the repository; do not duplicate it in memory.
- Never write Harness state into the repository.
- Treat `--repo` as a compatibility alias for `--project`.

Read [references/memory-lifecycle.md](references/memory-lifecycle.md) before resolving ambiguous classifications.
