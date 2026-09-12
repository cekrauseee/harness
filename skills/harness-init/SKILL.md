---
name: harness-init
description: Set up Harness project storage or change an existing project binding or host integration.
---

# Harness Init

Use this skill for setup or a binding change. Routine knowledge lookup can resolve storage directly without running setup. Commands below use this skill's `scripts/harness.py`; use its absolute path from another directory.

Resolve the intended project with `resolve --project /path/to/project`. If storage is needed for the authorized work and the project is unregistered, use `init --project /path/to/project`. Keep Harness state outside project files. Git worktrees share identity through the physical common Git directory; similar remote URLs do not establish identity.

For an identified additional folder, use `bind --project /new/path --project-id <id>`. Add `--replace /old/path` only for an intended replacement. This preserves identity and moves no files. Never infer a project ID; explicitly selected knowledge-only projects use `--project-id <id>`.

Read [host-integration.md](references/host-integration.md) only when installing or changing the host instruction. Setup or binding is complete when the intended identity resolves; host integration is complete when the edited instruction and installed paths are correct. One operation does not require repeating the others.

If stored metadata is malformed, inspect the reported problem within the requested repair scope. Preserve existing knowledge and ownership; do not reset an unreadable project to empty state. Use operation `--help` for syntax.
