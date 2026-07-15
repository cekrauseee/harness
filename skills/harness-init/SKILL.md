---
name: harness-init
description: Initialize, link, or inspect a repository's global Harness identity and install the automatic lifecycle adapter. Use for first-time Harness setup, after cloning or moving a repository, when hooks cannot resolve project context, or when checking the non-versioned project-to-Harness link.
---

# Harness Init

Initialize the global, file-native Harness without adding files to the repository. Treat this skill as setup and repair; normal lifecycle capture and recall run through hooks.

## Initialize

Run:

```bash
python3 scripts/init.py init --repo <repository> --json
```

The command:

- uses `${HARNESS_HOME:-~/.harness}`;
- assigns an opaque UUID;
- stores all Harness state under `projects/<uuid>/`;
- writes only `harness.project-id` to local Git config;
- creates no repository files and performs no legacy discovery or migration;
- installs or refreshes supported host lifecycle hooks while preserving unrelated hooks;
- is idempotent when the repository already points to a valid project.

Use `link --project-id <uuid>` only when the user has selected an existing Harness project. Use `resolve` to inspect the current link.

## Repair automatic lifecycle hooks

Initialization configures Codex and Claude Code automatically. To repair or refresh those hooks directly, run:

```bash
python3 scripts/install_hooks.py --host codex --host claude-code --json
```

Installation is idempotent and preserves unrelated host configuration. A full plugin installation can also discover `hooks/hooks.json` directly. The installed hooks call the normalized entrypoint:

```bash
python3 scripts/hook_adapter.py event session-start
python3 scripts/hook_adapter.py event user-prompt
python3 scripts/hook_adapter.py event pre-compact
python3 scripts/hook_adapter.py event stop
```

Hooks must fail open. They may initialize a new project or link an existing project only when the repository identity is unambiguous. Session start loads orientation, each user prompt loads task-specific context, and stop checkpoints the current session. Explicit summaries may become candidates; hooks never promote durable memory.

## Boundaries

- Never create `.harness`, `.project-harness`, or any other Harness file in the repository.
- Never import or migrate an earlier Project Harness layout.
- Never infer two projects are identical when multiple remote matches exist.
- Never ask routine lifecycle questions; report an actionable warning and let the host continue.
- Read [references/layout.md](references/layout.md) when inspecting or repairing storage.
