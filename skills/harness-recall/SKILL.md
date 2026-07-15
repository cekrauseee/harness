---
name: harness-recall
description: Recover task-relevant durable project memory and active handoffs from the global Harness under an explicit context budget. Use when automatic lifecycle recall is unavailable, when a fresh agent needs project continuity, or when manually inspecting exactly which stored context applies to a task.
---

# Harness Recall

Use this as a fallback or diagnostic surface. Automatic `SessionStart` and `PostCompact` hooks normally recall context.

## Recall scoped context

Always choose an explicit token budget:

```bash
python3 scripts/recall.py \
  --repo <repository> \
  --query "document the OAuth refresh flow" \
  --budget-tokens 1200 \
  --json
```

The command reads only active topic memories and active sessions. It never recalls unclassified candidates or archived entries. Results are ranked deterministically by lexical relevance, with active sessions favored, then packed without exceeding the requested approximate token budget.

Use text output when injecting the result into agent context. Use `--json` for automation and inspection. Treat `source` paths as traceability, not as repository paths.

## Rules

- Do not run without a deliberate budget.
- Prefer a concrete task query over a broad project name.
- Do not load the full Harness after a sparse recall.
- Do not treat an absent result as permission to infer project facts.
- Keep native host memory optional; Harness recall must stand on its own.

Read [references/selection.md](references/selection.md) when tuning a query or interpreting an empty result.
