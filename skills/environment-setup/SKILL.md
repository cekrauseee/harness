---
name: environment-setup
description: Establish or locate external project storage when setup is requested or useful context needs its first persistent home.
---

# Environment setup

Establish one external environment for the selected project. A Git repository, including a monorepo and all linked worktrees, is one project. Without Git, use the identified project directory. Separate projects keep separate environments and can reference one another explicitly.

Use this skill's helper by absolute path from other directories:

```bash
python3 scripts/harness.py resolve --project /path/to/project
python3 scripts/harness.py init --project /path/to/project
```

Resolve when the location is missing. Initialize only when setup is requested or persistent context or a checkout is needed for the authorized work; do not initialize merely to search for prior context. `init` reuses an existing binding. An explicit `--environment /external/directory` chooses a dedicated destination; never put environment state inside a target repository. The returned `worktrees` directory is the required parent for all new worktrees under the current local storage contract.

Setup creates only the binding, environment metadata and a short README. As useful material is added, maintain descriptive map links explaining when it applies; do not copy the linked facts into the map. Add knowledge or work files when they serve the task. Preserve existing environments and knowledge; a legacy or mismatched format needs a separate, deliberate conversion, not an automatic reset. The helper does not move projects or merge environments. Copying this local environment to another machine does not establish a shared project binding.

Return the resolved path and any relevant setup limitation, then continue the authorized work that needed storage. Setup does not create agents, checkouts, plans or a work record by itself. For a requested host-integration change, read [host integration](references/host-integration.md); preserve unrelated instructions and existing authority.
