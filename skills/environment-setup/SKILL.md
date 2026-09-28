---
name: environment-setup
description: Create or locate one external Harness environment for a project and all its Git worktrees.
---

# Environment setup

Establish one external environment for the selected project. A Git repository, including a monorepo and all linked worktrees, is one project. Without Git, use the identified project directory. Separate projects keep separate environments and can reference one another explicitly.

Use this skill's helper by absolute path from other directories:

```bash
python3 scripts/harness.py resolve --project /path/to/project
python3 scripts/harness.py init --project /path/to/project
```

Resolve when the location is missing. Initialize only when setup is requested or persistent context is needed for the authorized work. `init` reuses an existing binding. An explicit `--environment /external/directory` chooses a dedicated destination; never put environment state inside a target repository. The returned `worktrees` directory is the required parent for all new worktrees.

Setup creates only the binding, environment metadata and a short README. Add knowledge or work files when they serve the task. Preserve existing environments and knowledge; a legacy or mismatched format needs a separate, deliberate conversion, not an automatic reset. The helper does not move projects or merge environments.

Return the resolved path and any relevant setup limitation. Setup does not create agents, checkouts, plans or a work record by itself. For a requested host-integration change, read [host integration](references/host-integration.md); preserve unrelated instructions and existing authority.
