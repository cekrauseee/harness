---
name: harness-init
description: Locate or establish external Harness storage for a project, including non-Git folders and linked worktrees. Use for first setup or an explicit project binding change.
---

# Harness Init

Keep project knowledge outside its working files. Commands are relative to this installed skill directory; use its absolute script path from elsewhere.

```bash
python3 scripts/harness.py resolve --project /path/to/project
```

The result gives the project ID, knowledge directory and current workspace. Initialize an intended unregistered project with `init --project /path/to/project`. Git worktrees share identity through their physical common Git directory; ordinary folders use registered paths. Remote URL similarity is not identity evidence.

Use `resolve --project-id <id>` for an explicitly selected knowledge-only project. Project names and roots are in `project.json` under `${HARNESS_HOME:-~/.harness}/projects/`. Do not guess an ID or merge similar projects.

For an explicitly identified additional folder, use `bind --project /new/path --project-id <id>`. Add `--replace /old/path` only when replacing that binding is intended. The helper preserves identity, checks conflicts and refuses to replace a root with active contributions; it does not move files. Inspect the operation's `--help` if needed.

Read [host-integration.md](references/host-integration.md) when installing or updating the short host instruction. The agent edits that instruction through its existing file tools within the user's authorization. There is no installer, hook or background process.

Setup is complete when the intended identity resolves and the selected host reads the continuity instruction. No Harness files belong inside the project working tree.
