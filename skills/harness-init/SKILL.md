---
name: harness-init
description: Set up or repair shared Harness identity for a local project, including non-Git folders, worktrees and moved paths. Use for first setup, an unlinked project or host integration.
---

# Harness Init

Give the project a stable identity outside its files. Git and host IDs are optional. Commands below are relative to this installed skill directory; use its absolute `scripts/harness.py` path when working elsewhere. Python 3.10+ on macOS or Linux is required.

Inspect identity first:

```bash
python3 scripts/harness.py resolve --project /path/to/project
```

If the result is `not_initialized`, initialize the intended project:

```bash
python3 scripts/harness.py init --project /path/to/project
```

The result identifies the project and workspace. Two chats in the same folder share a workspace. Git worktrees share a project through their common Git directory and retain separate workspaces. Matching remote URLs do not join clones. Repeating initialization does not create a second identity.

For an explicitly identified existing project or a moved folder, inspect `guide` for `project.bind` or `project.move` before changing bindings. Do not infer an identity from a similar name. Missing, incomplete or unsupported state is an error to inspect, not permission to initialize a replacement identity.

## Make continuity part of the host workflow

Installing skills alone does not ensure they are called. Read [host-integration.md](references/host-integration.md) to preview, install, verify or remove a short instruction block in the explicitly selected host instruction file. Apply it only within the user's authorization to change that file. Installation preserves unrelated instructions and rejects edited or duplicate managed blocks. Hooks are not installed.

The integration calls for scope registration before shared writes and checkpoints after meaningful results and before delivery. Generic questions require no task administration. The scripts enforce consistency when called; agent participation remains cooperative.

Setup is complete when identity resolves and, if integration was requested, its status confirms an intact block and available runtime. No project metadata or operational state is written into the project.
