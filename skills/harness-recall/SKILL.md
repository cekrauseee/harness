---
name: harness-recall
description: Find and selectively load task-relevant Harness memory or handoffs. Use before work that may depend on prior project context, after compaction or host changes, or when continuity needs inspection.
---

# Harness Recall

Pull context only when the task suggests prior project knowledge may matter. Search semantic cards first, then hydrate only the selected record.

## Search cards

Use a concrete task query:

```bash
python3 scripts/recall.py \
  --project <project-path> \
  --json \
  search \
  --query "document the OAuth refresh flow" \
  --limit 3
```

Search returns compact cards without full content. Ranking is deterministic and lexical, with strong title, phrase, read-rule, and tag matches favored. Status and recency refine the result. A weak or absent match returns no cards.

## Hydrate a selection

After inspecting the cards, load only the record required for the task:

```bash
python3 scripts/recall.py \
  --project <project-path> \
  --json \
  hydrate \
  --id <memory-or-session-id> \
  --budget-tokens 1200
```

Choose the budget deliberately. Treat source and artifact references as traceability, not as automatic instructions to load more context. `--repo` remains a compatibility alias for `--project`.

## Rules

- Prefer a concrete task query over a broad project name.
- Hydrate no more than the smallest relevant card set, normally one record.
- Do not load the full Harness after a sparse or empty search.
- Do not treat an absent result as permission to infer project facts.
- Do not search every prompt; reuse verified context while it remains relevant.
- Keep native host memory optional; Harness recall must stand on its own.

Read [references/selection.md](references/selection.md) when tuning a query or interpreting an empty result.
