---
name: environment-knowledge
description: Preserve or correct confirmed durable internal knowledge by subject.
---

# Environment knowledge

Preserve information that will help later work and is absent from its canonical source. Start with a confirmed fact, decision, explanation or correction and its scope. Do not save raw conversations, secrets, reasoning traces or routine execution logs.

Use `knowledge/<subject>.md` inside the project's environment. Update the canonical subject instead of accumulating duplicate memories. Link to maintained source documentation when that is sufficient. Information intended for project developers, such as architecture, API contracts or development instructions, belongs in the repository; adapt it to that audience rather than copying an internal plan.

Resolve a missing location with this skill's `scripts/harness.py resolve --project /path/to/project`. For shared Markdown, read its observed hash and atomically update it:

```bash
python3 scripts/harness.py read --environment /path/to/environment --file knowledge/subject.md
python3 scripts/harness.py write --environment /path/to/environment --file knowledge/subject.md --expect <observed-sha256-or-missing> --input /path/to/content.md
```

Use the helper's absolute path outside this skill. On a conflict, inspect and incorporate the intervening change before retrying. Do not overwrite another writer's update. Keep only relevant context and uncertainty; omit a note when there is nothing useful to consolidate. Report the canonical file that changed.
