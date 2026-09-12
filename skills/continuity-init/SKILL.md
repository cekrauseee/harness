---
name: continuity-init
description: Create a shared environment, bind project folders or repositories, or update Continuity host integration.
---

# Continuity Init

Use this skill for environment setup or binding changes. Routine lookup can resolve storage directly. Commands use this skill's `scripts/continuity.py`; use its absolute path from another directory.

Create an environment for the explicitly selected projects with one operation:

```bash
python3 scripts/continuity.py init --name shared-work --project /work/app --project /work/docs
```

A single project is valid too. The environment shares knowledge and contributions across its members. Initialization reuses a common existing environment and adds unbound members. Projects already in different environments cause an error without changing bindings or moving knowledge. `--name` applies when creating an environment.

Use `resolve --project /path/to/project` to find the environment and current workspace. `resolve --environment-id <id>` lists its name and bound workspaces. Git worktrees share their repository's environment; similar remote URLs do not establish membership. Each project belongs to one environment.

To add another identified project, use `bind --project /new/path --environment-id <id>`. Add `--replace /old/path` only for an intended replacement; it preserves workspace identity and moves no files. Never guess an environment ID. Keep state outside project files under `${CONTINUITY_HOME:-~/.continuity}/environments/`.

Read [host-integration.md](references/host-integration.md) only when changing host instructions. Setup is complete when the selected projects resolve to the intended environment; it does not require repeating host setup.

If metadata is malformed, inspect the reported problem within the repair scope. Preserve knowledge and ownership instead of resetting state. Existing environments are not merged automatically. Use operation `--help` for syntax.
