---
name: harness-init
description: Initialize, link, resolve, or repair a local project's Harness identity without writing project metadata. Use for first setup, moved paths, host bindings, or unresolved continuity in Git and non-Git projects.
---

# Harness Init

Initialize the global, file-native Harness without adding metadata to the project. Treat this skill as setup, binding, and repair. Normal recall is agent-initiated and does not depend on hooks.

## Initialize

Run:

```bash
python3 scripts/init.py init --project <project-path> --json
```

The command:

- uses `${HARNESS_HOME:-~/.harness}`;
- assigns an opaque UUID;
- stores all Harness state under `projects/<uuid>/`;
- registers the project path as a machine-local binding;
- can also register host identity and retain a legacy Git link when available;
- creates no project files;
- is idempotent when the path already resolves to a valid project.

Use `link --project-id <uuid>` only when an existing Harness project has been selected. Use `resolve` to inspect identity without mutation. Resolution priority is explicit UUID, host binding, nearest registered path ancestor, then legacy Git identity.

`--repo` remains a compatibility alias for `--project`.

## Optional lifecycle adapters

Harness does not require hooks. When a host supports silent lifecycle maintenance, install or refresh its adapters explicitly:

```bash
python3 scripts/install_hooks.py --host codex --host claude-code --json
```

The explicit command is the only supported installation path. It is idempotent and preserves unrelated host configuration.

Adapters must fail open and remain model-silent. They may maintain timestamps or clean temporary workspace files. They must not inject memory, create empty sessions, initialize an unrelated path, persist raw host messages, or promote durable memory.

## Boundaries

- Never create `.harness`, `.project-harness`, or any other Harness file in the project.
- Never infer two projects are identical when multiple remote matches exist.
- Do not require Git, a remote, or a lifecycle hook.
- Never ask routine lifecycle questions; report an actionable warning and let the host continue.
- Read [references/layout.md](references/layout.md) when inspecting or repairing storage.
