---
name: environment-knowledge
description: Preserve confirmed reusable project decisions or findings, and correct outdated internal knowledge.
---

# Environment knowledge

Preserve information that will help later work and is absent from its canonical source, without waiting for a separate save request when losing it would cause meaningful loss. Start with a confirmed fact, decision, explanation or correction and its scope. Temporary investigation, unresolved hypotheses and current execution status belong in work context when worth retaining, not in durable knowledge. Do not save raw conversations, secrets, reasoning traces or routine execution logs.

Use `knowledge/<subject>.md` inside the project's environment. Update the canonical subject instead of accumulating duplicate memories. Link to maintained source documentation when that is sufficient. Keep the environment map useful for discovery with a descriptive link when adding or changing a subject's applicability. A fundamental rule may live in the map itself; reference it rather than duplicating it. Information intended for project developers, such as architecture, API contracts or development instructions, belongs in the repository; adapt it to that audience rather than copying an internal plan.

Resolve a missing location with this skill's `scripts/harness.py resolve --project /path/to/project`. If no binding exists and useful material must persist, the same helper's `init --project /path/to/project` establishes the external environment. For shared Markdown, read its observed hash and atomically update it:

```bash
python3 scripts/harness.py read --environment /path/to/environment --file knowledge/subject.md
python3 scripts/harness.py write --environment /path/to/environment --file knowledge/subject.md --expect <observed-sha256-or-missing> --input /path/to/content.md
```

Use the helper's absolute path outside this skill. On a conflict, inspect and incorporate the intervening change before retrying. Do not overwrite another writer's update. Omit a note when there is nothing useful to consolidate. Report the confirmed canonical save or the specific failure; an uncertain write is not successful persistence and does not justify a competing copy. Continue the broader authorized objective after consolidation.
